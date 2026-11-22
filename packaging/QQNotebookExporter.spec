# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
RESOURCE_DIR = ROOT / "src" / "qq_notebook_exporter" / "resources"

playwright_datas, playwright_binaries, playwright_hidden = collect_all("playwright")
docx_datas, docx_binaries, docx_hidden = collect_all("docx")

datas = [
    (str(RESOURCE_DIR / "app.png"), "qq_notebook_exporter/resources"),
    (str(RESOURCE_DIR / "app.ico"), "qq_notebook_exporter/resources"),
    *playwright_datas,
    *docx_datas,
]
binaries = [*playwright_binaries, *docx_binaries]
hiddenimports = [
    "qq_notebook_exporter.resources",
    *playwright_hidden,
    *docx_hidden,
]

a = Analysis(
    [str(ROOT / "src" / "qq_notebook_exporter" / "desktop" / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "tests"],
    noarchive=False,
)
external_icu_names = {"icudt78.dll", "icuuc.dll"}
a.binaries = [
    entry
    for entry in a.binaries
    if Path(entry[0]).name.casefold() not in external_icu_names
]
a.datas = [
    entry
    for entry in a.datas
    if Path(entry[0]).name.casefold() not in external_icu_names
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QQNotebookExporter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(RESOURCE_DIR / "app.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="QQNotebookExporter",
)
