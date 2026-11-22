from types import SimpleNamespace

import pytest

from qq_notebook_exporter.browser import (
    BrowserSession,
    find_sid_candidates_in_cookies,
    find_sid_candidates_in_url,
    find_sid_in_cookies,
    find_sid_in_url,
    wait_for_valid_sid,
)
from qq_notebook_exporter.errors import AuthenticationRequiredError, QQMailTransportError


def test_find_sid_in_url_query_and_fragment() -> None:
    assert find_sid_in_url("https://wx.mail.qq.com/webnote?sid=query-value&x=1") == "query-value"
    assert find_sid_in_url("https://wx.mail.qq.com/webnote#sid=fragment-value") == "fragment-value"
    assert find_sid_in_url("https://wx.mail.qq.com/webnote") is None


def test_find_sid_candidates_preserve_all_url_values() -> None:
    url = "https://wx.mail.qq.com/webnote?sid=first&SID=first#sid=second"

    assert find_sid_candidates_in_url(url) == ["first", "second"]


def test_find_sid_in_cookies_prefers_qq_mail_domain() -> None:
    cookies = [
        {"name": "sid", "value": "generic", "domain": ".qq.com", "expires": 2_000_000_100},
        {"name": "sid", "value": "mail", "domain": ".mail.qq.com", "expires": 2_000_000_000},
    ]

    assert find_sid_in_cookies(cookies) == "mail"


def test_find_sid_in_cookies_uses_latest_expiry_within_same_priority() -> None:
    cookies = [
        {"name": "SID", "value": "old", "domain": ".qq.com", "expires": 2_000_000_000},
        {"name": "sid", "value": "new", "domain": ".qq.com", "expires": 2_000_000_100},
    ]

    assert find_sid_in_cookies(cookies) == "new"
    assert find_sid_in_cookies([]) is None


def test_find_sid_candidates_skip_rejected_expired_cookie() -> None:
    cookies = [
        {"name": "sid", "value": "expired", "domain": ".mail.qq.com", "expires": 50},
        {"name": "sid", "value": "fresh", "domain": ".qq.com", "expires": 200},
    ]

    assert find_sid_candidates_in_cookies(cookies, now=100) == ["fresh"]


def test_wait_for_valid_sid_retries_stale_session() -> None:
    candidate_sets = iter([["stale", "fresh"], ["stale", "fresh"]])
    attempts: list[str] = []

    def find_sids() -> list[str]:
        return next(candidate_sets, [])

    def validate_sid(sid: str) -> None:
        attempts.append(sid)
        if sid == "stale":
            raise AuthenticationRequiredError("expired")

    sid = wait_for_valid_sid(
        find_sids=find_sids,
        validate_sid=validate_sid,
        timeout_seconds=1,
        interval_seconds=0,
        sleep=lambda _: None,
    )

    assert sid == "fresh"
    assert attempts == ["stale", "fresh"]


def test_wait_for_valid_sid_raises_after_timeout() -> None:
    with pytest.raises(AuthenticationRequiredError, match="未检测到可用"):
        wait_for_valid_sid(
            find_sids=lambda: [],
            validate_sid=lambda _: None,
            timeout_seconds=0,
        )


def test_fetch_binary_uses_context_request_and_preserves_body(tmp_path) -> None:
    calls: list[tuple[str, dict]] = []

    class Response:
        ok = True
        status = 200

        @staticmethod
        def body() -> bytes:
            return b"original-image-bytes"

    class Request:
        @staticmethod
        def get(url: str, **kwargs) -> Response:
            calls.append((url, kwargs))
            return Response()

    session = BrowserSession(tmp_path)
    session._context = SimpleNamespace(request=Request())

    result = session.fetch_binary("//cdn.example.test/photo.jpg")

    assert result == b"original-image-bytes"
    assert calls[0][0] == "https://cdn.example.test/photo.jpg"
    assert calls[0][1]["headers"]["Referer"] == "https://wx.mail.qq.com/"


def test_fetch_binary_rejects_failed_response(tmp_path) -> None:
    class Response:
        ok = False
        status = 403

    class Request:
        @staticmethod
        def get(_url: str, **_kwargs) -> Response:
            return Response()

    session = BrowserSession(tmp_path)
    session._context = SimpleNamespace(request=Request())

    with pytest.raises(QQMailTransportError, match="HTTP 403"):
        session.fetch_binary("https://cdn.example.test/photo.jpg")
