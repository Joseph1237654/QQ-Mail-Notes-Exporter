from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from qq_notebook_exporter import __version__
from qq_notebook_exporter.browser import LOGIN_URL, WEBNOTE_ORIGIN, BrowserSession
from qq_notebook_exporter.config import Settings
from qq_notebook_exporter.docx_exporter import DocxExporter
from qq_notebook_exporter.errors import (
    AuthenticationRequiredError,
    BrowserLaunchError,
    QQNotebookExporterError,
)
from qq_notebook_exporter.gateway import QQMailNotebookGateway
from qq_notebook_exporter.models import NoteSummary
from qq_notebook_exporter.workflow import ExportService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qq-notebook-export",
        description="将 QQ 邮箱记事本逐条导出为保留标题的 Word 文档。",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    login = subparsers.add_parser("login", help="打开浏览器并保存 QQ 邮箱登录态")
    _add_browser_options(login)
    login.add_argument("--timeout", type=int, default=None, help="登录等待秒数，默认 600")

    export = subparsers.add_parser("export", help="批量导出为 Word 文档")
    _add_browser_options(export)
    export.add_argument("--output", type=Path, default=None, help="Word 输出目录")
    export.add_argument("--limit", type=int, default=None, help="仅导出前 N 条")
    export.add_argument("--overwrite", action="store_true", help="覆盖已存在的文件")
    export.add_argument(
        "--delay",
        type=float,
        default=None,
        help="接口请求最小间隔秒数，默认 1.25",
    )
    export.add_argument("--headless", action="store_true", help="无头运行，不推荐")

    doctor = subparsers.add_parser("doctor", help="检查本地运行环境")
    _add_browser_options(doctor)
    doctor.add_argument("--output", type=Path, default=None, help="Word 输出目录")

    return parser


def _add_browser_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", type=Path, default=None, help="浏览器配置目录")
    parser.add_argument(
        "--channel",
        choices=("msedge", "chromium"),
        default=None,
        help="浏览器通道，默认 msedge",
    )


def _settings_from_args(args: argparse.Namespace) -> Settings:
    settings = Settings()
    changes = {}
    if getattr(args, "output", None) is not None:
        changes["output_dir"] = args.output
    if getattr(args, "profile", None) is not None:
        changes["profile_dir"] = args.profile
    if getattr(args, "channel", None) is not None:
        changes["browser_channel"] = args.channel
    if getattr(args, "headless", False):
        changes["headless"] = True
    if getattr(args, "delay", None) is not None:
        changes["request_delay"] = max(0.0, args.delay)
    if getattr(args, "timeout", None) is not None:
        changes["login_timeout"] = max(1, args.timeout)
    settings = replace(settings, **changes)
    settings.ensure_directories()
    return settings


def _run_login(args: argparse.Namespace, settings: Settings) -> int:
    print("正在打开 Microsoft Edge。")
    print("请在浏览器中登录 QQ 邮箱，并进入记事本。")
    print("工具检测到 sid 后还会调用接口验证登录是否真实可用。")

    with BrowserSession(
        settings.profile_dir,
        channel=settings.browser_channel,
        headless=False,
        timeout_ms=settings.page_timeout_ms,
    ) as session:
        session.goto(LOGIN_URL)

        def validate_sid(sid: str) -> None:
            gateway = QQMailNotebookGateway(session, sid, request_delay=0)
            total = gateway.validate_session()
            print(f"登录态验证通过，首屏可读取记事本 {total} 条。")

        session.wait_for_valid_sid(settings.login_timeout, validate_sid)
        print("登录态已保存。")
    return 0


def _run_export(args: argparse.Namespace, settings: Settings) -> int:
    settings.ensure_directories()
    print(f"输出目录: {settings.output_dir}")

    with BrowserSession(
        settings.profile_dir,
        channel=settings.browser_channel,
        headless=settings.headless,
        timeout_ms=settings.page_timeout_ms,
    ) as session:
        session.goto(f"{WEBNOTE_ORIGIN}/")
        sid = session.wait_for_sid(5)
        gateway = QQMailNotebookGateway(
            session,
            sid,
            request_delay=settings.request_delay,
        )
        service = ExportService(gateway, DocxExporter(session.fetch_binary))

        print("正在读取记事本列表...")
        report = service.run(
            settings.output_dir,
            limit=args.limit,
            overwrite=args.overwrite,
            progress=_print_progress,
        )

    print()
    print(
        f"完成：共 {report.total} 条，导出 {report.exported} 条，"
        f"跳过 {report.skipped} 条，失败 {report.failed} 条。"
    )
    if report.failures:
        print("失败明细：")
        for failure in report.failures:
            print(f"  - [{failure.note_id}] {failure.title}: {failure.message}")
        return 1
    return 0


def _print_progress(index: int, total: int, summary: NoteSummary, status: str) -> None:
    print(f"[{index:>4}/{total:<4}] {status}: {summary.display_title}")


def _run_doctor(settings: Settings) -> int:
    checks = [
        ("Python", sys.version.split()[0], True),
        ("python-docx", _package_version("docx"), _module_available("docx")),
        ("BeautifulSoup", _package_version("bs4"), _module_available("bs4")),
        ("Playwright", _package_version("playwright"), _module_available("playwright")),
        ("Edge", _find_edge() or "未找到", _find_edge() is not None),
    ]

    print("运行环境检查：")
    for name, detail, ok in checks:
        marker = "OK" if ok else "MISSING"
        print(f"  [{marker:>7}] {name}: {detail}")
    print(f"  浏览器通道: {settings.browser_channel or 'chromium'}")
    print(f"  登录配置: {settings.profile_dir}")
    print(f"  输出目录: {settings.output_dir}")
    requires_edge = settings.browser_channel == "msedge"
    return 0 if all(ok for _, _, ok in checks if requires_edge or _ != "Edge") else 1


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _package_version(module_name: str) -> str:
    if not _module_available(module_name):
        return "未安装"
    try:
        from importlib.metadata import version

        package_names = {
            "docx": "python-docx",
            "bs4": "beautifulsoup4",
            "playwright": "playwright",
        }
        return version(package_names[module_name])
    except Exception:
        return "已安装"


def _find_edge() -> str | None:
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = _settings_from_args(args)

    try:
        if args.command == "login":
            return _run_login(args, settings)
        if args.command == "export":
            return _run_export(args, settings)
        if args.command == "doctor":
            return _run_doctor(settings)
        parser.error(f"未知命令: {args.command}")
    except AuthenticationRequiredError as exc:
        print(f"登录态不可用: {exc}", file=sys.stderr)
        print("请先执行: qq-notebook-export login", file=sys.stderr)
        return 2
    except BrowserLaunchError as exc:
        print(f"浏览器错误: {exc}", file=sys.stderr)
        return 3
    except QQNotebookExporterError as exc:
        print(f"导出失败: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return 130
    return 0
