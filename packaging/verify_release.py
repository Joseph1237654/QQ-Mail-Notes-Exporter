from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "browser-profile",
    "docs",
    "exports",
    "tests",
}
FORBIDDEN_FILE_NAMES = {
    "cookies",
    "cookies-journal",
    "history",
    "login data",
    "login data-journal",
    "web data",
    "web data-journal",
}
FORBIDDEN_SUFFIXES = {
    ".coverage",
    ".db",
    ".docx",
    ".har",
    ".log",
    ".pdf",
    ".sqlite",
    ".sqlite3",
}
REQUIRED_FILES = {
    "QQNotebookExporter.exe",
    "_internal/qq_notebook_exporter/resources/app.ico",
    "_internal/qq_notebook_exporter/resources/app.png",
}
ALLOWED_ARTIFACT_PATHS = {
    "_internal/docx/templates/default.docx",
}


class ReleaseVerificationError(RuntimeError):
    """Raised when a release directory contains unsafe or incomplete files."""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    root: Path
    file_count: int
    total_bytes: int


def verify_release(
    root: Path,
    *,
    private_markers: tuple[str, ...] = (),
) -> VerificationResult:
    resolved_root = root.resolve()
    if not resolved_root.is_dir():
        raise ReleaseVerificationError(f"发布目录不存在: {resolved_root}")

    errors: list[str] = []
    files = [path for path in resolved_root.rglob("*") if path.is_file()]
    for file_path in files:
        relative = file_path.relative_to(resolved_root)
        for part in relative.parts[:-1]:
            if part.casefold() in FORBIDDEN_DIRECTORY_NAMES:
                errors.append(f"禁止的目录: {relative}")
                break

        name = file_path.name.casefold()
        if name in FORBIDDEN_FILE_NAMES:
            errors.append(f"禁止的隐私文件: {relative}")
        if (
            file_path.suffix.casefold() in FORBIDDEN_SUFFIXES
            and relative.as_posix() not in ALLOWED_ARTIFACT_PATHS
        ):
            errors.append(f"禁止的产物类型: {relative}")

        data = file_path.read_bytes()
        for marker in private_markers:
            encoded = marker.encode("utf-8")
            if encoded and encoded in data:
                errors.append(f"发现隐私路径标记 {marker!r}: {relative}")

    missing = sorted(
        required
        for required in REQUIRED_FILES
        if not (resolved_root / required).is_file()
    )
    for relative in missing:
        errors.append(f"缺少发布文件: {relative}")

    if errors:
        raise ReleaseVerificationError("\n".join(errors))

    return VerificationResult(
        root=resolved_root,
        file_count=len(files),
        total_bytes=sum(path.stat().st_size for path in files),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a packaged release directory.")
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("--private-marker", action="append", default=[])
    args = parser.parse_args()

    try:
        result = verify_release(
            args.release_dir,
            private_markers=tuple(args.private_marker),
        )
    except ReleaseVerificationError as exc:
        print(exc)
        return 1

    print(
        json.dumps(
            {
                "release_dir": str(result.root),
                "file_count": result.file_count,
                "total_mb": round(result.total_bytes / 1024 / 1024, 2),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
