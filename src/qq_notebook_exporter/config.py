from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR_NAME = "QQNotebookExporter"


def default_profile_dir() -> Path:
    override = os.getenv("QQNE_PROFILE_DIR")
    if override:
        return Path(override).expanduser()

    local_app_data = os.getenv("LOCALAPPDATA")
    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / APP_DIR_NAME / "browser-profile"

    return Path.home() / ".local" / "share" / "qq-notebook-exporter" / "browser-profile"


def default_output_dir() -> Path:
    override = os.getenv("QQNE_OUTPUT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.cwd() / "exports"


@dataclass(frozen=True, slots=True)
class Settings:
    output_dir: Path = field(default_factory=default_output_dir)
    profile_dir: Path = field(default_factory=default_profile_dir)
    browser_channel: str | None = "msedge"
    headless: bool = False
    request_delay: float = 0.35
    login_timeout: int = 600
    page_timeout_ms: int = 45_000

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profile_dir.parent.mkdir(parents=True, exist_ok=True)
