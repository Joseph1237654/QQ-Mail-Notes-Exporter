from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "packaging" / "QQNotebookExporter.spec"
DIST_ROOT = ROOT / "dist"
RELEASE_APP_DIR = DIST_ROOT / "QQNotebookExporter"
WORK_ROOT = ROOT / "build" / "pyinstaller"
RELEASE_ROOT = ROOT / "release"
VERSION_INFO = ROOT / "packaging" / "version_info.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows application.")
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Also compile the Inno Setup installer when ISCC is available.",
    )
    args = parser.parse_args()

    if os.name != "nt":
        raise SystemExit("Windows packaging must run on Windows.")
    if not SPEC_PATH.is_file() or not VERSION_INFO.is_file():
        raise SystemExit("Packaging files are missing.")

    version = _package_version()
    _verify_version_file(version)
    _reset_directory(RELEASE_APP_DIR)
    _reset_directory(WORK_ROOT)

    pyinstaller = [sys.executable, "-m", "PyInstaller"]
    _run(
        [
            *pyinstaller,
            "--noconfirm",
            "--clean",
            "--distpath",
            str(DIST_ROOT),
            "--workpath",
            str(WORK_ROOT),
            str(SPEC_PATH),
        ]
    )
    _run_release_verification()

    if args.installer:
        _build_installer(version)

    print(f"Portable release: {RELEASE_APP_DIR}")
    if args.installer:
        print(f"Installer output: {RELEASE_ROOT}")
    return 0


def _package_version() -> str:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(metadata["project"]["version"])


def _verify_version_file(version: str) -> None:
    content = VERSION_INFO.read_text(encoding="utf-8")
    compact_version = f"({version.replace('.', ', ')}, 0)" if version.count(".") == 2 else ""
    if version not in content or (compact_version and compact_version not in content):
        raise SystemExit(
            f"packaging/version_info.txt does not match project version {version}."
        )


def _run_release_verification() -> None:
    module_path = ROOT / "packaging" / "verify_release.py"
    spec = importlib.util.spec_from_file_location("verify_release", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load release verifier.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    private_markers = (
        str(Path.home()),
        str(Path.home() / "AppData" / "Local" / "QQNotebookExporter"),
        "all-557-images-v2",
        "full-export-second",
    )
    try:
        result = module.verify_release(
            RELEASE_APP_DIR,
            private_markers=private_markers,
        )
    except module.ReleaseVerificationError as exc:
        raise SystemExit(f"Release privacy verification failed:\n{exc}") from exc
    print(
        f"Release verified: {result.file_count} files, "
        f"{result.total_bytes / 1024 / 1024:.2f} MB"
    )


def _build_installer(version: str) -> None:
    compiler = _find_iscc()
    if compiler is None:
        raise SystemExit(
            "Inno Setup compiler not found. Install Inno Setup 6 or set "
            "INNO_SETUP_COMPILER to ISCC.exe."
        )
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(compiler),
            f"/DAppVersion={version}",
            f"/O{RELEASE_ROOT}",
            str(ROOT / "packaging" / "installer.iss"),
        ]
    )


def _find_iscc() -> Path | None:
    override = os.getenv("INNO_SETUP_COMPILER")
    candidates = [
        Path(override) if override else None,
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    found = shutil.which("ISCC.exe")
    return Path(found) if found else None


def _reset_directory(path: Path) -> None:
    resolved = path.resolve()
    allowed_roots = (DIST_ROOT.resolve(), WORK_ROOT.resolve())
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise SystemExit(f"Refusing to remove unexpected path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def _run(command: list[str]) -> None:
    print("+", subprocess.list2cmdline(command))
    env = os.environ.copy()
    windows_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
    env["PATH"] = os.pathsep.join(
        [
            str(Path(sys.executable).parent),
            str(windows_root / "System32"),
            str(windows_root),
            str(windows_root / "System32" / "Wbem"),
            str(windows_root / "System32" / "WindowsPowerShell" / "v1.0"),
        ]
    )
    subprocess.run(command, cwd=ROOT, check=True, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
