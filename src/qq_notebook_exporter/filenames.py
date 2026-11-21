from __future__ import annotations

import re
import unicodedata

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")
TRAILING_DOTS_OR_SPACES = re.compile(r"[ .]+$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename_stem(value: str, *, max_length: int = 100) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = WHITESPACE.sub(" ", normalized).strip()
    normalized = INVALID_FILENAME_CHARS.sub("_", normalized)
    normalized = TRAILING_DOTS_OR_SPACES.sub("", normalized)

    if not normalized:
        normalized = "无标题"

    if normalized.upper() in WINDOWS_RESERVED_NAMES:
        normalized = f"_{normalized}"

    if len(normalized) > max_length:
        normalized = normalized[:max_length].rstrip(" .")
    return normalized or "无标题"


def build_note_filename(title: str, note_id: str) -> str:
    title_stem = safe_filename_stem(title, max_length=100)
    raw_id = note_id.lstrip("_") or "note"
    id_stem = safe_filename_stem(raw_id, max_length=40)
    return f"{title_stem}__{id_stem}.docx"
