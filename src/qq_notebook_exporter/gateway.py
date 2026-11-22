from __future__ import annotations

import time
from typing import Any, Protocol

from qq_notebook_exporter.errors import (
    AuthenticationRequiredError,
    QQMailAPIError,
    QQMailRateLimitError,
    QQMailTransportError,
)
from qq_notebook_exporter.models import Note, NoteSummary, parse_timestamp

BASE_URL = "https://wx.mail.qq.com"
PAGE_SIZE = 50
RECORD_COLLECTION_KEYS = ("infos", "list", "notes", "items")
CONTENT_KEYS = ("content", "note_content", "html", "text", "body")


class JsonTransport(Protocol):
    def post_form_json(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """Post one form-encoded QQ Mail request and return JSON."""


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
        max_retries: int = 4,
        retry_backoff: float = 0.5,
        rate_limit_backoff: float = 30.0,
    ) -> None:
        if not sid.strip():
            raise AuthenticationRequiredError("QQ 邮箱 sid 为空。")
        self.transport = transport
        self.sid = sid.strip()
        self.request_delay = max(0.0, request_delay)
        self.page_size = max(1, min(page_size, PAGE_SIZE))
        self.max_retries = max(0, max_retries)
        self.retry_backoff = max(0.0, retry_backoff)
        self.rate_limit_backoff = max(0.0, rate_limit_backoff)
        self._last_request_at: float | None = None

    def list_notes(self) -> list[NoteSummary]:
        notes: list[NoteSummary] = []
        seen_note_ids: set[str] = set()
        page_now = 0
        total: int | None = None

        while True:
            body = self._request(
                "/webnote/list",
                {
                    "func": 1,
                    "page_now": page_now,
                    "page_size": self.page_size,
                    "sort_direction": 2,
                    "sort_field": 1,
                },
            )
            infos = self._extract_records(body)

            added_this_page = 0
            for item in infos:
                try:
                    summary = NoteSummary.from_api(item)
                except ValueError:
                    continue
                if summary.note_id in seen_note_ids:
                    continue
                seen_note_ids.add(summary.note_id)
                notes.append(summary)
                added_this_page += 1

            page_total = self._as_int(body.get("total_affected_count"))
            if page_total is not None:
                total = page_total
            if (
                not infos
                or added_this_page == 0
                or (total is not None and len(notes) >= total)
            ):
                break

            page_now += 1

        return notes

    def validate_session(self) -> int:
        body = self._request(
            "/webnote/list",
            {
                "func": 1,
                "page_now": 0,
                "page_size": 50,
                "sort_direction": 2,
                "sort_field": 1,
            },
        )
        total = self._as_int(body.get("total_affected_count"))
        if total is not None:
            return total
        return len(self._extract_records(body))

    def read_note(self, summary: NoteSummary) -> Note:
        body = self._request("/webnote/read", {"noteid": summary.note_id})
        record = self._select_record(body, summary.note_id)

        content: str | None = None
        for key in CONTENT_KEYS:
            value = record.get(key)
            if isinstance(value, str):
                content = value
                break
        if content is None:
            raise QQMailAPIError(
                f"笔记 {summary.note_id} 的完整正文缺失，拒绝使用摘要导出。"
            )

        subject = str(record.get("subject") or summary.subject).strip()
        category_id = self._as_int(record.get("cataid"))
        if category_id is None:
            category_id = summary.category_id
        category_name = str(record.get("cata_name") or summary.category_name).strip()

        return Note(
            note_id=str(record.get("noteid") or summary.note_id),
            subject=subject,
            content=content,
            category_id=category_id,
            category_name=category_name,
            created_at=parse_timestamp(record.get("ctime")) or summary.created_at,
            updated_at=parse_timestamp(record.get("utime")) or summary.updated_at,
        )

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        data = {
            "language": "zh",
            "r": int(time.time() * 1000),
            "sid": self.sid,
            **params,
        }
        url = f"{BASE_URL}{path}"
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                payload = self.transport.post_form_json(url, data)
                return self._checked_body(payload)
            except QQMailRateLimitError:
                if attempt >= self.max_retries:
                    raise
                self._slow_down_after_rate_limit()
                if self.rate_limit_backoff:
                    time.sleep(self.rate_limit_backoff * (2**attempt))
            except QQMailTransportError:
                if attempt >= self.max_retries:
                    raise
                if self.retry_backoff:
                    time.sleep(self.retry_backoff * (2**attempt))
        raise AssertionError("unreachable")

    def _throttle(self) -> None:
        if self.request_delay <= 0:
            return
        now = time.monotonic()
        if self._last_request_at is not None:
            remaining = self.request_delay - (now - self._last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def _slow_down_after_rate_limit(self) -> None:
        if self.request_delay <= 0:
            return
        self.request_delay = min(max(self.request_delay * 2, 0.75), 2.0)

    @staticmethod
    def _checked_body(payload: dict[str, Any]) -> dict[str, Any]:
        head = payload.get("head")
        if not isinstance(head, dict):
            raise QQMailAPIError("QQ 记事本接口缺少 head 字段。")

        ret = QQMailNotebookGateway._as_int(head.get("ret"))
        if ret == -20002:
            message = str(head.get("msg") or "登录态已失效。")
            raise AuthenticationRequiredError(message)
        if ret == -20003:
            message = str(head.get("msg") or "操作过于频繁，请稍后再试。")
            raise QQMailRateLimitError(message)
        if ret != 0:
            message = str(head.get("msg") or "未知错误")
            raise QQMailAPIError(f"QQ 记事本接口错误 ret={ret}: {message}")

        body = payload.get("body")
        if not isinstance(body, dict):
            raise QQMailAPIError("QQ 记事本接口缺少 body 字段。")
        return body

    @staticmethod
    def _extract_records(body: dict[str, Any]) -> list[dict[str, Any]]:
        for key in RECORD_COLLECTION_KEYS:
            if key not in body:
                continue
            value = body[key]
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                return [value]
            raise QQMailAPIError(f"QQ 记事本接口字段 {key} 格式异常。")
        return []

    @classmethod
    def _select_record(cls, body: dict[str, Any], note_id: str) -> dict[str, Any]:
        records = cls._extract_records(body)
        if not records:
            return body
        for record in records:
            if str(record.get("noteid") or record.get("note_id") or "") == note_id:
                return record
        return records[0]

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
