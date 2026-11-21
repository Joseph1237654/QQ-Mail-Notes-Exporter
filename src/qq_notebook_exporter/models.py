from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_datetime(value: Any) -> datetime | None:
    seconds = _optional_int(value)
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class NoteSummary:
    note_id: str
    subject: str
    digest: str = ""
    category_id: int | None = None
    category_name: str = ""
    is_starred: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    size: int | None = None

    @property
    def display_title(self) -> str:
        return self.subject.strip() or "无标题"

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> NoteSummary:
        note_id = _clean_text(payload.get("noteid") or payload.get("note_id"))
        if not note_id:
            raise ValueError("QQ Mail note payload does not contain noteid")

        return cls(
            note_id=note_id,
            subject=_clean_text(payload.get("subject")),
            digest=_clean_text(payload.get("digest")),
            category_id=_optional_int(payload.get("cataid")),
            category_name=_clean_text(payload.get("cata_name")),
            is_starred=bool(_optional_int(payload.get("is_star"))),
            created_at=_optional_datetime(payload.get("ctime")),
            updated_at=_optional_datetime(payload.get("utime")),
            size=_optional_int(payload.get("size")),
        )


@dataclass(frozen=True, slots=True)
class Note:
    note_id: str
    subject: str
    content: str
    category_id: int | None = None
    category_name: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def display_title(self) -> str:
        return self.subject.strip() or "无标题"
