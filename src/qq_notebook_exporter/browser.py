from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from qq_notebook_exporter.errors import (
    AuthenticationRequiredError,
    BrowserLaunchError,
    QQMailAPIError,
)

LOGIN_URL = "https://mail.qq.com/"
WEBNOTE_ORIGIN = "https://wx.mail.qq.com"


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
        if self._context is None:
            return None

        for cookie in self._context.cookies():
            if str(cookie.get("name", "")).lower() == "sid":
                value = str(cookie.get("value", "")).strip()
                if value:
                    return value

        if self.page is not None:
            query = parse_qs(urlparse(self.page.url).query)
            values = query.get("sid") or query.get("SID")
            if values and values[0].strip():
                return values[0].strip()
        return None

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

    def fetch_json(self, url: str) -> dict[str, Any]:
        if self.page is None:
            raise BrowserLaunchError("浏览器页面尚未初始化。")

        if not self.page.url.startswith(WEBNOTE_ORIGIN):
            self.goto(f"{WEBNOTE_ORIGIN}/")

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

        if not isinstance(result, dict):
            raise QQMailAPIError("页面内请求没有返回有效结果。")

        status = int(result.get("status", 0))
        text = str(result.get("text", "")).lstrip("\ufeff")
        if status >= 400:
            raise QQMailAPIError(f"QQ 记事本接口 HTTP 状态异常: {status}")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise QQMailAPIError("QQ 记事本接口返回了非 JSON 内容，登录态可能已失效。") from exc

        if not isinstance(payload, dict):
            raise QQMailAPIError("QQ 记事本接口返回格式异常。")
        return payload
