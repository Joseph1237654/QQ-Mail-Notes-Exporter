from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO_ROOT / "packaging" / "verify_release.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_release", VERIFIER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_verifier_accepts_clean_application_tree(tmp_path) -> None:
    verifier = _load_verifier()
    release = _build_release_tree(tmp_path)

    result = verifier.verify_release(release)

    assert result.file_count == 3
    assert result.total_bytes > 0


def test_release_verifier_allows_python_docx_default_template(tmp_path) -> None:
    verifier = _load_verifier()
    release = _build_release_tree(tmp_path)
    template = release / "_internal" / "docx" / "templates" / "default.docx"
    template.parent.mkdir(parents=True)
    template.write_bytes(b"library-template")

    result = verifier.verify_release(release)

    assert result.file_count == 4


@pytest.mark.parametrize(
    ("relative_path", "message"),
    [
        ("exports/note.docx", "禁止的目录"),
        ("_internal/session.log", "禁止的产物类型"),
        ("_internal/browser-profile/Cookies", "禁止的目录"),
    ],
)
def test_release_verifier_rejects_private_artifacts(
    tmp_path,
    relative_path: str,
    message: str,
) -> None:
    verifier = _load_verifier()
    release = _build_release_tree(tmp_path)
    artifact = release / relative_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"private")

    with pytest.raises(verifier.ReleaseVerificationError, match=message):
        verifier.verify_release(release)


def test_release_verifier_rejects_known_private_path_marker(tmp_path) -> None:
    verifier = _load_verifier()
    release = _build_release_tree(tmp_path)
    (release / "_internal" / "data.bin").write_bytes(b"prefix C:\\Users\\private suffix")

    with pytest.raises(verifier.ReleaseVerificationError, match="隐私路径标记"):
        verifier.verify_release(
            release,
            private_markers=("C:\\Users\\private",),
        )


def test_release_verifier_requires_application_executable(tmp_path) -> None:
    verifier = _load_verifier()
    release = tmp_path / "release"
    release.mkdir()

    with pytest.raises(verifier.ReleaseVerificationError, match="缺少发布文件"):
        verifier.verify_release(release)


def _build_release_tree(tmp_path: Path) -> Path:
    release = tmp_path / "release"
    resources = release / "_internal" / "qq_notebook_exporter" / "resources"
    resources.mkdir(parents=True)
    (release / "QQNoteExporter.exe").write_bytes(b"exe")
    (resources / "app.ico").write_bytes(b"ico")
    (resources / "app.png").write_bytes(b"png")
    return release
