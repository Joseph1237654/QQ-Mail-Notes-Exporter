from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from qq_notebook_exporter.browser import LOGIN_URL, WEBNOTE_ORIGIN, BrowserSession
from qq_notebook_exporter.config import Settings
from qq_notebook_exporter.docx_exporter import DocxExporter
from qq_notebook_exporter.gateway import QQMailNotebookGateway
from qq_notebook_exporter.workflow import ExportReport, ExportService


class LoginWorker(QThread):
    succeeded = Signal(int)
    failed = Signal(str)

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings

    def run(self) -> None:
        try:
            total = 0
            with BrowserSession(
                self.settings.profile_dir,
                channel=self.settings.browser_channel,
                headless=False,
                timeout_ms=self.settings.page_timeout_ms,
            ) as session:
                session.goto(LOGIN_URL)

                def validate_sid(sid: str) -> None:
                    nonlocal total
                    gateway = QQMailNotebookGateway(session, sid, request_delay=0)
                    total = gateway.validate_session()

                session.wait_for_valid_sid(self.settings.login_timeout, validate_sid)
            self.succeeded.emit(total)
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)


class ExportWorker(QThread):
    progress = Signal(int, int, str, str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        settings: Settings,
        output_dir: Path,
        *,
        overwrite: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> None:
        try:
            with BrowserSession(
                self.settings.profile_dir,
                channel=self.settings.browser_channel,
                headless=self.settings.headless,
                timeout_ms=self.settings.page_timeout_ms,
            ) as session:
                session.goto(f"{WEBNOTE_ORIGIN}/")
                sid = session.wait_for_sid(5)
                gateway = QQMailNotebookGateway(
                    session,
                    sid,
                    request_delay=self.settings.request_delay,
                )
                service = ExportService(gateway, DocxExporter())
                report: ExportReport = service.run(
                    self.output_dir,
                    overwrite=self.overwrite,
                    progress=self._emit_progress,
                )
            self.succeeded.emit(report)
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)

    def _emit_progress(self, index: int, total: int, summary, status: str) -> None:
        self.progress.emit(index, total, status, summary.display_title)
