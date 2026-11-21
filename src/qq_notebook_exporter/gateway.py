from __future__ import annotations

import time
from typing import Any, Protocol
from urllib.parse import urlencode

from qq_notebook_exporter.errors import (
    AuthenticationRequiredError,
    QQMailAPIError,
    QQMailTransportError,
)
from qq_notebook_exporter.models import Note, NoteSummary, parse_timestamp

BASE_URL = "https://wx.mail.qq.com"
PAGE_SIZE = 40


class JsonTransport(Protocol):
    def fetch_json(self, url: str) -> dict[str, Any]:
        """Fetch one QQ Mail JSON endpoint."""


class NoteSource(Protocol):
    def list_notes(self) -> list[NoteSummary]:
        """Return all available notebook entries."""

    def read_note(self, summary: NoteSummary) -> Note:
        """Read the complete content of one notebook entry."""


class QQMailNotebookGateway:
    def __init__(
        self,
        transport: JsonTransport,
        sid: str,
        *,
        request_delay: float = 0.35,
        page_size: int = PAGE_SIZE,
        max_retries: int = 2,
        retry_backoff: float = 0.5,
    ) -> None:
        if not sid.strip():
            raise AuthenticationRequiredError("QQ 邮箱 sid 为空。")
        self.transport = transport
        self.sid = sid.strip()
        self.request_delay = max(0.0, request_delay)
        self.page_size = max(1, min(page_size, PAGE_SIZE))
        self.max_retries = max(0, max_retries)
        self.retry_backoff = max(0.0, retry_backoff)

    def list_notes(self) -> list[NoteSummary]:
        notes: list[NoteSummary] = []
        seen_note_ids: set[str] = set()
        offset = 0

        while True:
            payload = self._request(
                "/webnote/list",
                {"offset": offset, "limit": self.page_size},
            )
            body = self._checked_body(payload)
            infos = body.get("infos") or []
            if not isinstance(infos, list):
                raise QQMailAPIError("记事本列表字段 infos 格式异常。")

            added_this_page = 0
            for item in infos:
                if not isinstance(item, dict):
                    continue
                try:
                    summary = NoteSummary.from_api(item)
                except ValueError:
                    continue
                if summary.note_id in seen_note_ids:
                    continue
                seen_note_ids.add(summary.note_id)
                notes.append(summary)
                added_this_page += 1

            total = self._as_int(body.get("total_affected_count"))
            if (
                not infos
                or added_this_page == 0
                or (total is not None and len(notes) >= total)
            ):
                break

            offset += len(infos)
            if self.request_delay:
                time.sleep(self.request_delay)

        return notes

    def validate_session(self) -> int:
        payload = self._request("/webnote/list", {"offset": 0, "limit": 1})
        body = self._checked_body(payload)
        return self._as_int(body.get("total_affected_count")) or 0

    def read_note(self, summary: NoteSummary) -> Note:
        payload = self._request("/webnote/read", {"noteid": summary.note_id})
        body = self._checked_body(payload)

        content = ""
        for key in ("content", "note_content", "html", "text", "body"):
            value = body.get(key)
            if isinstance(value, str) and value:
                content = value
                break
        if not content:
            content = summary.digest

        subject = str(body.get("subject") or summary.subject).strip()
        category_id = self._as_int(body.get("cataid"))
        if category_id is None:
            category_id = summary.category_id
        category_name = str(body.get("cata_name") or summary.category_name).strip()

        return Note(
            note_id=str(body.get("noteid") or summary.note_id),
            subject=subject,
            content=content,
            category_id=category_id,
            category_name=category_name,
            created_at=parse_timestamp(body.get("ctime")) or summary.created_at,
            updated_at=parse_timestamp(body.get("utime")) or summary.updated_at,
        )

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = {"sid": self.sid, **params}
        url = f"{BASE_URL}{path}?{urlencode(query)}"
        for attempt in range(self.max_retries + 1):
            try:
                return self.transport.fetch_json(url)
            except QQMailTransportError:
                if attempt >= self.max_retries:
                    raise
                if self.retry_backoff:
                    time.sleep(self.retry_backoff * (2**attempt))
        raise AssertionError("unreachable")

    @staticmethod
    def _checked_body(payload: dict[str, Any]) -> dict[str, Any]:
        head = payload.get("head")
        if not isinstance(head, dict):
            raise QQMailAPIError("QQ 记事本接口缺少 head 字段。")

        ret = QQMailNotebookGateway._as_int(head.get("ret"))
        if ret == -20002:
            message = str(head.get("msg") or "登录态已失效。")
            raise AuthenticationRequiredError(message)
        if ret != 0:
            message = str(head.get("msg") or "未知错误")
            raise QQMailAPIError(f"QQ 记事本接口错误 ret={ret}: {message}")

        body = payload.get("body")
        if not isinstance(body, dict):
            raise QQMailAPIError("QQ 记事本接口缺少 body 字段。")
        return body

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
