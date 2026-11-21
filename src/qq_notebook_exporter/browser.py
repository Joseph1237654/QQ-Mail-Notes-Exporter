from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from qq_notebook_exporter.errors import (
    AuthenticationRequiredError,
    BrowserLaunchError,
    QQMailAPIError,
    QQMailTransportError,
)

LOGIN_URL = "https://mail.qq.com/"
WEBNOTE_ORIGIN = "https://wx.mail.qq.com"


def find_sid_in_url(url: str) -> str | None:
    candidates = find_sid_candidates_in_url(url)
    return candidates[0] if candidates else None


def find_sid_candidates_in_url(url: str) -> list[str]:
    parsed = urlparse(url)
    candidates: list[str] = []
    for component in (parsed.query, parsed.fragment):
        params = parse_qs(component)
        for key in ("sid", "SID", "Sid"):
            values = params.get(key)
            for value in values or []:
                cleaned = value.strip()
                if cleaned and cleaned not in candidates:
                    candidates.append(cleaned)
    return candidates


def find_sid_in_cookies(cookies: Iterable[Mapping[str, Any]]) -> str | None:
    candidates = find_sid_candidates_in_cookies(cookies)
    return candidates[0] if candidates else None


def find_sid_candidates_in_cookies(
    cookies: Iterable[Mapping[str, Any]],
    *,
    now: float | None = None,
) -> list[str]:
    current_time = time.time() if now is None else now
    candidates: list[tuple[int, float, str]] = []
    for cookie in cookies:
        if str(cookie.get("name", "")).lower() != "sid":
            continue

        value = str(cookie.get("value", "")).strip()
        if not value:
            continue

        domain = str(cookie.get("domain", "")).lower().lstrip(".")
        if domain == "wx.mail.qq.com":
            domain_priority = 3
        elif domain == "mail.qq.com" or domain.endswith(".mail.qq.com"):
            domain_priority = 2
        elif domain == "qq.com" or domain.endswith(".qq.com"):
            domain_priority = 1
        else:
            domain_priority = 0

        try:
            expires = float(cookie.get("expires") or 0)
        except (TypeError, ValueError):
            expires = 0.0
        if 0 < expires < current_time:
            continue
        candidates.append((domain_priority, expires, value))

    ordered = sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True)
    result: list[str] = []
    for _, _, value in ordered:
        if value not in result:
            result.append(value)
    return result


def _unique_values(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def wait_for_valid_sid(
    *,
    find_sids: Callable[[], list[str]],
    validate_sid: Callable[[str], None],
    timeout_seconds: int,
    interval_seconds: float = 1.0,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    deadline = monotonic() + timeout_seconds
    last_error: AuthenticationRequiredError | None = None
    rejected_sids: set[str] = set()

    while monotonic() < deadline:
        for sid in find_sids():
            if sid in rejected_sids:
                continue
            try:
                validate_sid(sid)
                return sid
            except AuthenticationRequiredError as exc:
                last_error = exc
                rejected_sids.add(sid)

        sleep(interval_seconds)

    message = "未检测到可用的 QQ 邮箱登录态。请完成登录并进入记事本页面。"
    raise AuthenticationRequiredError(message) from last_error


class BrowserSession:
    """Persistent Edge session with API requests executed inside the page."""

    def __init__(
        self,
        profile_dir: Path,
        *,
        channel: str | None = "msedge",
        headless: bool = False,
        timeout_ms: int = 45_000,
    ) -> None:
        self.profile_dir = Path(profile_dir)
        self.channel = channel
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright: Any = None
        self._context: Any = None
        self.page: Any = None

    def __enter__(self) -> BrowserSession:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserLaunchError(
                "未安装 Playwright。请执行: python -m pip install -e ."
            ) from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()

        launch_options: dict[str, Any] = {
            "user_data_dir": str(self.profile_dir),
            "headless": self.headless,
            "accept_downloads": True,
            "no_viewport": True,
            "timeout": self.timeout_ms,
        }
        if self.channel:
            launch_options["channel"] = self.channel

        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                **launch_options
            )
        except Exception as exc:
            self._stop_playwright()
            raise BrowserLaunchError(
                "无法启动浏览器。请确认 Microsoft Edge 已安装，"
                "或尝试参数 --channel chromium。"
            ) from exc

        pages = self._context.pages
        self.page = pages[0] if pages else self._context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        del exc_type, exc, traceback
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            finally:
                self._context = None
        self._stop_playwright()

    def _stop_playwright(self) -> None:
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            finally:
                self._playwright = None

    def goto(self, url: str) -> None:
        if self.page is None:
            raise BrowserLaunchError("浏览器页面尚未初始化。")
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except Exception as exc:
            raise BrowserLaunchError(f"无法打开页面: {url}") from exc

    def find_sid(self) -> str | None:
        candidates = self.find_sids()
        return candidates[0] if candidates else None

    def find_sids(self) -> list[str]:
        if self._context is None:
            return []

        candidates: list[str] = []
        if self.page is not None:
            candidates.extend(find_sid_candidates_in_url(self.page.url))
        candidates.extend(find_sid_candidates_in_cookies(self._context.cookies()))
        return _unique_values(candidates)

    def wait_for_sid(self, timeout_seconds: int, interval_seconds: float = 1.0) -> str:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            sid = self.find_sid()
            if sid:
                return sid
            time.sleep(interval_seconds)

        raise AuthenticationRequiredError(
            "未检测到 QQ 邮箱登录态。请重新执行 login，并完成登录和记事本页面加载。"
        )

    def wait_for_valid_sid(
        self,
        timeout_seconds: int,
        validator: Callable[[str], None],
        interval_seconds: float = 1.0,
    ) -> str:
        return wait_for_valid_sid(
            find_sids=self.find_sids,
            validate_sid=validator,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
        )

    def fetch_json(self, url: str) -> dict[str, Any]:
        if self.page is None:
            raise BrowserLaunchError("浏览器页面尚未初始化。")

        if not self.page.url.startswith(WEBNOTE_ORIGIN):
            self.goto(f"{WEBNOTE_ORIGIN}/")

        try:
            result = self.page.evaluate(
                """
                async ({ url }) => {
                    const response = await fetch(url, {
                        method: "GET",
                        credentials: "include",
                        headers: { "Accept": "application/json" }
                    });
                    return {
                        status: response.status,
                        text: await response.text()
                    };
                }
                """,
                {"url": url},
            )
        except Exception as exc:
            raise QQMailTransportError("QQ 记事本接口请求失败，可稍后重试。") from exc

        if not isinstance(result, dict):
            raise QQMailAPIError("页面内请求没有返回有效结果。")

        status = int(result.get("status", 0))
        text = str(result.get("text", "")).lstrip("\ufeff")
        if status == 429 or status >= 500:
            raise QQMailTransportError(f"QQ 记事本接口暂时不可用: HTTP {status}")
        if status >= 400:
            raise QQMailAPIError(f"QQ 记事本接口 HTTP 状态异常: {status}")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise QQMailAPIError("QQ 记事本接口返回了非 JSON 内容，登录态可能已失效。") from exc

        if not isinstance(payload, dict):
            raise QQMailAPIError("QQ 记事本接口返回格式异常。")
        return payload
