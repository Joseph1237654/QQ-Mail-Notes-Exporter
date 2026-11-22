from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from qq_notebook_exporter.errors import (
    AuthenticationRequiredError,
    QQMailAPIError,
    QQMailRateLimitError,
    QQMailTransportError,
)
from qq_notebook_exporter.gateway import QQMailNotebookGateway
from qq_notebook_exporter.models import NoteSummary

FIXTURES = Path(__file__).parent / "fixtures"


class FakeTransport:
    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self.payloads = payloads
        self.urls: list[str] = []
        self.requests: list[dict[str, Any]] = []

    def post_form_json(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        self.urls.append(url)
        self.requests.append(data)
        for path, payload in self.payloads.items():
            if path in url:
                return payload
        raise AssertionError(f"Unexpected URL: {url}")


class SequenceTransport:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.requests: list[dict[str, Any]] = []

    def post_form_json(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        del url
        self.requests.append(data)
        return self.payloads.pop(0)


class FlakyTransport:
    def __init__(self, payload: dict[str, Any], failures: int) -> None:
        self.payload = payload
        self.failures = failures
        self.calls = 0

    def post_form_json(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        del url
        del data
        self.calls += 1
        if self.calls <= self.failures:
            raise QQMailTransportError("temporary")
        return self.payload


class RateLimitThenSuccessTransport:
    def __init__(self) -> None:
        self.calls = 0

    def post_form_json(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        del url, data
        self.calls += 1
        if self.calls == 1:
            return {
                "head": {
                    "ret": -20003,
                    "msg": "操作过于频繁，请稍后再试。",
                }
            }
        return {
            "head": {"ret": 0},
            "body": {"total_affected_count": 0, "infos": []},
        }


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_list_notes_parses_one_page() -> None:
    transport = FakeTransport(
        {
            "/webnote/list": {
                "head": {"ret": 0},
                "body": {
                    "total_affected_count": 1,
                    "infos": [
                        {
                            "noteid": "_7",
                            "subject": "标题",
                            "digest": "摘要",
                            "cataid": 1,
                            "cata_name": "默认笔记",
                        }
                    ],
                },
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    notes = gateway.list_notes()

    assert len(notes) == 1
    assert notes[0].display_title == "标题"
    assert transport.requests[0]["sid"] == "sid-value"
    assert transport.requests[0]["page_now"] == 0
    assert transport.requests[0]["page_size"] == 50
    assert transport.requests[0]["sort_field"] == 1


def test_list_notes_uses_sanitized_fixture_and_keeps_empty_title_fallback() -> None:
    transport = FakeTransport({"/webnote/list": load_fixture("qqmail_list.json")})
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    notes = gateway.list_notes()

    assert [note.note_id for note in notes] == ["_1001", "_1002"]
    assert notes[0].display_title == "示例笔记一"
    assert notes[1].display_title == "无标题"


def test_read_note_uses_content_before_alternatives() -> None:
    transport = FakeTransport(
        {
            "/webnote/read": {
                "head": {"ret": 0},
                "body": {
                    "noteid": "_7",
                    "subject": "读取标题",
                    "content": "<p>完整正文</p>",
                    "text": "备用正文",
                    "cata_name": "工作",
                },
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    note = gateway.read_note(NoteSummary(note_id="_7", subject="列表标题"))

    assert note.subject == "读取标题"
    assert note.content == "<p>完整正文</p>"
    assert note.category_name == "工作"


def test_read_note_uses_fixture_metadata() -> None:
    transport = FakeTransport({"/webnote/read": load_fixture("qqmail_read.json")})
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    note = gateway.read_note(NoteSummary(note_id="_1001", subject="旧标题"))

    assert note.subject == "示例笔记一"
    assert note.content.startswith("<p>脱敏正文</p>")
    assert note.updated_at is not None


def test_read_note_accepts_body_list_record() -> None:
    transport = FakeTransport({"/webnote/read": load_fixture("qqmail_read_list.json")})
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    note = gateway.read_note(NoteSummary(note_id="_1001", subject="旧标题"))

    assert note.note_id == "_1001"
    assert note.subject == "列表示例"
    assert note.content == "<p>脱敏正文</p><p>第二段</p>"
    assert note.category_name == "工作"


def test_read_note_selects_matching_body_list_record() -> None:
    transport = FakeTransport(
        {
            "/webnote/read": {
                "head": {"ret": 0},
                "body": {
                    "list": [
                        {"noteid": "_other", "subject": "其他", "content": "其他正文"},
                        {"noteid": "_target", "subject": "目标", "content": "目标正文"},
                    ]
                },
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    note = gateway.read_note(NoteSummary(note_id="_target", subject="列表标题"))

    assert note.subject == "目标"
    assert note.content == "目标正文"


def test_read_note_rejects_missing_full_content() -> None:
    transport = FakeTransport(
        {
            "/webnote/read": {
                "head": {"ret": 0},
                "body": {"noteid": "_7", "subject": "只有摘要"},
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    with pytest.raises(QQMailAPIError, match="拒绝使用摘要导出"):
        gateway.read_note(NoteSummary(note_id="_7", subject="标题", digest="预览摘要"))


def test_read_note_accepts_explicit_empty_content() -> None:
    transport = FakeTransport(
        {
            "/webnote/read": {
                "head": {"ret": 0},
                "body": {"noteid": "_7", "subject": "空笔记", "content": ""},
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    note = gateway.read_note(NoteSummary(note_id="_7", subject="标题"))

    assert note.content == ""


def test_expired_sid_raises_authentication_error() -> None:
    transport = FakeTransport(
        {
            "/webnote/list": {
                "head": {"ret": -20002, "msg": "登录态失效，请重新登录。"},
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "expired", request_delay=0)

    with pytest.raises(AuthenticationRequiredError, match="登录态失效"):
        gateway.list_notes()


def test_validate_session_returns_note_count() -> None:
    transport = FakeTransport(
        {
            "/webnote/list": {
                "head": {"ret": 0},
                "body": {"total_affected_count": 726, "infos": []},
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "valid", request_delay=0)

    assert gateway.validate_session() == 726
    assert transport.requests[0]["page_now"] == 0
    assert transport.requests[0]["page_size"] == 50


def test_validate_session_uses_first_page_when_total_is_missing() -> None:
    transport = FakeTransport(
        {
            "/webnote/list": {
                "head": {"ret": 0},
                "body": {
                    "infos": [
                        {"noteid": "_1", "subject": "第一条"},
                        {"noteid": "_2", "subject": "第二条"},
                    ],
                },
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    assert gateway.validate_session() == 2


def test_list_notes_skips_malformed_entries() -> None:
    transport = FakeTransport(
        {
            "/webnote/list": {
                "head": {"ret": 0},
                "body": {
                    "total_affected_count": 1,
                    "infos": [
                        {"subject": "缺少 noteid"},
                        {"noteid": "_valid", "subject": "有效笔记"},
                    ],
                },
            }
        }
    )
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    notes = gateway.list_notes()

    assert [note.note_id for note in notes] == ["_valid"]


def test_list_notes_stops_when_server_repeats_a_page() -> None:
    first_page = {
        "head": {"ret": 0},
        "body": {
            "total_affected_count": 3,
            "infos": [{"noteid": "_1", "subject": "第一条"}],
        },
    }
    second_page = {
        "head": {"ret": 0},
        "body": {
            "total_affected_count": 3,
            "infos": [
                {"noteid": "_1", "subject": "第一条"},
                {"noteid": "_2", "subject": "第二条"},
            ],
        },
    }
    transport = SequenceTransport([first_page, second_page, second_page])
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    notes = gateway.list_notes()

    assert [note.note_id for note in notes] == ["_1", "_2"]
    assert [request["page_now"] for request in transport.requests] == [0, 1, 2]


def test_list_notes_fetches_all_post_pages() -> None:
    pages = [
        {
            "head": {"ret": 0},
            "body": {
                "total_affected_count": 3,
                "infos": [
                    {"noteid": "_1", "subject": "第一条"},
                    {"noteid": "_2", "subject": "第二条"},
                ],
            },
        },
        {
            "head": {"ret": 0},
            "body": {"infos": [{"noteid": "_3", "subject": "第三条"}]},
        },
    ]
    transport = SequenceTransport(pages)
    gateway = QQMailNotebookGateway(transport, "sid-value", request_delay=0)

    notes = gateway.list_notes()

    assert [note.note_id for note in notes] == ["_1", "_2", "_3"]
    assert [request["page_now"] for request in transport.requests] == [0, 1]


def test_transient_error_is_retried() -> None:
    payload = {
        "head": {"ret": 0},
        "body": {"total_affected_count": 0, "infos": []},
    }
    transport = FlakyTransport(payload, failures=2)
    gateway = QQMailNotebookGateway(
        transport,
        "sid-value",
        request_delay=0,
        max_retries=2,
        retry_backoff=0,
    )

    assert gateway.list_notes() == []
    assert transport.calls == 3


def test_rate_limit_response_is_retried() -> None:
    transport = RateLimitThenSuccessTransport()
    gateway = QQMailNotebookGateway(
        transport,
        "sid-value",
        request_delay=0,
        max_retries=1,
        rate_limit_backoff=0,
    )

    assert gateway.list_notes() == []
    assert transport.calls == 2


def test_rate_limit_exhaustion_raises_transport_error() -> None:
    class AlwaysRateLimited:
        def post_form_json(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
            del url, data
            return {"head": {"ret": -20003, "msg": "操作过于频繁"}}

    gateway = QQMailNotebookGateway(
        AlwaysRateLimited(),
        "sid-value",
        request_delay=0,
        max_retries=1,
        rate_limit_backoff=0,
    )

    with pytest.raises(QQMailRateLimitError):
        gateway.list_notes()
