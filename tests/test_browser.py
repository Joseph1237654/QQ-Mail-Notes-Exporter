import pytest

from qq_notebook_exporter.browser import (
    find_sid_in_cookies,
    find_sid_in_url,
    wait_for_valid_sid,
)
from qq_notebook_exporter.errors import AuthenticationRequiredError


def test_find_sid_in_url_query_and_fragment() -> None:
    assert find_sid_in_url("https://wx.mail.qq.com/webnote?sid=query-value&x=1") == "query-value"
    assert find_sid_in_url("https://wx.mail.qq.com/webnote#sid=fragment-value") == "fragment-value"
    assert find_sid_in_url("https://wx.mail.qq.com/webnote") is None


def test_find_sid_in_cookies_prefers_qq_mail_domain() -> None:
    cookies = [
        {"name": "sid", "value": "generic", "domain": ".qq.com", "expires": 999},
        {"name": "sid", "value": "mail", "domain": ".mail.qq.com", "expires": 100},
    ]

    assert find_sid_in_cookies(cookies) == "mail"


def test_find_sid_in_cookies_uses_latest_expiry_within_same_priority() -> None:
    cookies = [
        {"name": "SID", "value": "old", "domain": ".qq.com", "expires": 100},
        {"name": "sid", "value": "new", "domain": ".qq.com", "expires": 200},
    ]

    assert find_sid_in_cookies(cookies) == "new"
    assert find_sid_in_cookies([]) is None


def test_wait_for_valid_sid_retries_stale_session() -> None:
    candidates = iter(["stale", "stale", "fresh"])
    attempts: list[str] = []

    def find_sid() -> str | None:
        return next(candidates, None)

    def validate_sid(sid: str) -> None:
        attempts.append(sid)
        if sid == "stale":
            raise AuthenticationRequiredError("expired")

    sid = wait_for_valid_sid(
        find_sid=find_sid,
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
            find_sid=lambda: None,
            validate_sid=lambda _: None,
            timeout_seconds=0,
        )
