from __future__ import annotations

from typing import Any

import pytest

from qq_notebook_exporter.errors import AuthenticationRequiredError
from qq_notebook_exporter.gateway import QQMailNotebookGateway


class FakeTransport:
    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self.payloads = payloads
        self.urls: list[str] = []

    def fetch_json(self, url: str) -> dict[str, Any]:
        self.urls.append(url)
        for path, payload in self.payloads.items():
            if path in url:
                return payload
        raise AssertionError(f"Unexpected URL: {url}")


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
    assert "sid=sid-value" in transport.urls[0]
    assert "limit=40" in transport.urls[0]


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

    from qq_notebook_exporter.models import NoteSummary

    note = gateway.read_note(NoteSummary(note_id="_7", subject="列表标题"))

    assert note.subject == "读取标题"
    assert note.content == "<p>完整正文</p>"
    assert note.category_name == "工作"


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
    assert "limit=1" in transport.urls[0]
