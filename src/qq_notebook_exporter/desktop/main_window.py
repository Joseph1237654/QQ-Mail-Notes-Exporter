from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from qq_notebook_exporter.config import Settings
from qq_notebook_exporter.desktop.i18n import (
    DEFAULT_LANGUAGE,
    normalize_language,
    translate,
    translate_runtime_message,
)
from qq_notebook_exporter.desktop.icon import app_logo_pixmap, load_app_icon, settings_gear_icon
from qq_notebook_exporter.desktop.settings_dialog import SettingsDialog
from qq_notebook_exporter.desktop.workers import ExportWorker, LoginWorker
from qq_notebook_exporter.workflow import ExportReport


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Settings | None = None,
        preferences: QSettings | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings or Settings()
        self.settings.ensure_directories()
        self._worker: LoginWorker | ExportWorker | None = None
        self._logged_in = False
        self._output_dir = self.settings.output_dir
        self._last_output_dir: Path | None = None
        # Preserve the existing organization key so user preferences survive the rename.
        self._preferences = preferences or QSettings(
            "QQNotebookExporter",
            "QQMailNotebookExporter",
        )
        self.language = normalize_language(
            self._preferences.value("language", DEFAULT_LANGUAGE),
        )
        self._header_status_key = "header.logged_out"
        self._account_state_key = "account.not_signed_in"
        self._account_state_values: dict[str, object] = {}
        self._current_item_key = "current.waiting_start"
        self._current_item_values: dict[str, object] = {}

        self.setWindowTitle(self._t("app.brand"))
        self.setWindowIcon(load_app_icon())
        self.setMinimumSize(QSize(900, 620))
        self.resize(1040, 720)
        self._restore_preferences()
        self._build_ui()
        self._apply_language()
        self._apply_idle_state()

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content(), 1)
        root_layout.addLayout(body, 1)
        self.setCentralWidget(root)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(86)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 16, 28, 16)
        layout.setSpacing(14)

        logo = QLabel()
        logo.setObjectName("AppIcon")
        logo.setFixedSize(40, 40)
        logo.setPixmap(app_logo_pixmap(40, "#D2D2D2"))
        logo.setAccessibleName(self._t("app.icon_accessible"))
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        self.brand_label = QLabel(self._t("app.brand"))
        self.brand_label.setObjectName("Brand")
        layout.addWidget(self.brand_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        self.header_status = QLabel(self._t(self._header_status_key))
        self.header_status.setObjectName("HeaderStatus")
        layout.addWidget(self.header_status, 0, Qt.AlignmentFlag.AlignVCenter)
        return header

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(320)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        self.account_label = QLabel(self._t("sections.account"))
        self.account_label.setObjectName("SectionLabel")
        layout.addWidget(self.account_label)

        self.account_state = QLabel(self._t(self._account_state_key))
        self.account_state.setObjectName("Muted")
        layout.addWidget(self.account_state)

        self.login_button = QPushButton(self._t("buttons.login"))
        self.login_button.setObjectName("Primary")
        self.login_button.clicked.connect(self._start_login)
        layout.addWidget(self.login_button)

        layout.addWidget(_rule())
        self.export_label = QLabel(self._t("sections.export"))
        self.export_label.setObjectName("SectionLabel")
        layout.addWidget(self.export_label)

        self.export_button = QPushButton(self._t("buttons.start_export"))
        self.export_button.setObjectName("Primary")
        self.export_button.clicked.connect(self._start_export)
        layout.addWidget(self.export_button)

        layout.addStretch(1)
        self.settings_button = QPushButton()
        self.settings_button.setObjectName("SettingsButton")
        self.settings_button.setIcon(settings_gear_icon())
        self.settings_button.setIconSize(QSize(27, 27))
        self.settings_button.setAccessibleName(self._t("buttons.open_settings"))
        self.settings_button.setToolTip(self._t("buttons.open_settings"))
        self.settings_button.setFixedSize(40, 40)
        self.settings_button.clicked.connect(self._open_settings)
        layout.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignLeft)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        content.setObjectName("Content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        metrics = QHBoxLayout()
        metrics.setSpacing(36)
        self.total_value, self.total_label = self._add_metric(metrics, "metrics.total")
        self.exported_value, self.exported_label = self._add_metric(
            metrics,
            "metrics.exported",
        )
        self.failed_value, self.failed_label = self._add_metric(metrics, "metrics.failed")
        metrics.addStretch(1)
        layout.addLayout(metrics)
        layout.addWidget(_rule())

        progress_header = QHBoxLayout()
        self.progress_label = QLabel(self._t("sections.progress"))
        self.progress_label.setObjectName("SectionLabel")
        self.progress_percent = QLabel("0%")
        self.progress_percent.setObjectName("Muted")
        progress_header.addWidget(self.progress_label)
        progress_header.addStretch(1)
        progress_header.addWidget(self.progress_percent)
        layout.addLayout(progress_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.current_item = QLabel(self._t(self._current_item_key))
        self.current_item.setObjectName("CurrentItem")
        self.current_item.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(self.current_item)

        activity_header = QHBoxLayout()
        self.activity_label = QLabel(self._t("sections.activity"))
        self.activity_label.setObjectName("SectionLabel")
        self.open_directory_button = QPushButton(self._t("buttons.open_folder"))
        self.open_directory_button.setObjectName("Ghost")
        self.open_directory_button.clicked.connect(self._open_output_directory)
        activity_header.addWidget(self.activity_label)
        activity_header.addStretch(1)
        activity_header.addWidget(self.open_directory_button)
        layout.addLayout(activity_header)

        self.activity_log = QPlainTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setPlaceholderText(self._t("activity.placeholder"))
        layout.addWidget(self.activity_log, 1)
        return content

    def _add_metric(
        self,
        layout: QHBoxLayout,
        label_key: str,
    ) -> tuple[QLabel, QLabel]:
        box = QVBoxLayout()
        box.setSpacing(0)
        value = QLabel("0")
        value.setObjectName("MetricValue")
        label = QLabel(self._t(label_key))
        label.setObjectName("MetricLabel")
        box.addWidget(value)
        box.addWidget(label)
        layout.addLayout(box)
        return value, label

    def _start_login(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._set_busy("header.waiting_login")
        self._set_account_state("account.waiting_browser")
        self._set_current_item("current.complete_sign_in")
        self._append_log(self._t("log.login_opening"))

        worker = LoginWorker(self.settings, self)
        worker.succeeded.connect(self._login_succeeded)
        worker.failed.connect(self._task_failed)
        worker.finished.connect(self._worker_finished)
        self._worker = worker
        worker.start()

    def _start_export(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if not self._logged_in:
            self._append_log(self._t("log.login_required"))
            return

        output_dir = self._output_dir
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error(
                self._t("error.create_output_dir", error=exc),
            )
            return

        self._last_output_dir = output_dir
        self._preferences.setValue("output_dir", str(output_dir))
        self._reset_progress()
        self._set_busy("header.exporting")
        self._append_log(self._t("log.export_started", path=output_dir))

        worker = ExportWorker(self.settings, output_dir, parent=self)
        worker.progress.connect(self._update_progress)
        worker.succeeded.connect(self._export_succeeded)
        worker.failed.connect(self._task_failed)
        worker.finished.connect(self._worker_finished)
        self._worker = worker
        worker.start()

    def _login_succeeded(self, total: int) -> None:
        self._logged_in = True
        self._set_header_status("header.logged_in")
        self._set_account_state("account.readable", total=total)
        self._set_current_item("current.session_verified")
        self._append_log(self._t("log.login_succeeded", total=total))
        self._apply_idle_state()

    def _export_succeeded(self, report: ExportReport) -> None:
        self.total_value.setText(str(report.total))
        self.exported_value.setText(str(report.exported))
        self.failed_value.setText(str(report.failed))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_percent.setText("100%")
        self._set_current_item("current.export_complete")
        self._set_header_status("header.completed")
        self._last_output_dir = self._output_dir
        self._append_log(
            self._t(
                "log.export_finished",
                exported=report.exported,
                skipped=report.skipped,
                failed=report.failed,
            ),
        )
        for failure in report.failures:
            self._append_log(
                self._t(
                    "log.failure",
                    note_id=failure.note_id,
                    title=failure.title,
                    message=self._runtime_message(failure.message),
                ),
            )
        self._apply_idle_state()

    def _update_progress(self, index: int, total: int, status: str, title: str) -> None:
        percent = int(index * 100 / total) if total else 0
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        self.progress_percent.setText(f"{percent}%")
        self.total_value.setText(str(total))
        self._set_current_item(
            "current.progress",
            index=index,
            total=total,
            status=self._status_text(status),
            title=title,
        )
        if status == "失败":
            self._append_log(self._t("log.progress_failure", title=title))

    def _task_failed(self, message: str) -> None:
        message = self._runtime_message(message)
        self._set_header_status("header.error")
        self._set_account_state("account.task_failed")
        self._set_current_item("current.task_failed")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_percent.setText("0%")
        self._append_log(self._t("log.error", message=message))
        self._show_error(message)
        self._apply_idle_state()

    def _worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._apply_idle_state()

    def _set_busy(self, status_key: str) -> None:
        self._set_header_status(status_key)
        self.login_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_percent.setText(self._t("progress.processing"))

    def _apply_idle_state(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.login_button.setEnabled(True)
        self.export_button.setEnabled(self._logged_in)
        self.settings_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)

    def _reset_progress(self) -> None:
        self.total_value.setText("0")
        self.exported_value.setText("0")
        self.failed_value.setText("0")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_percent.setText("0%")
        self._set_current_item("current.preparing")

    def _open_output_directory(self) -> None:
        directory = self._last_output_dir or self._output_dir
        if directory.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _open_settings(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        dialog = SettingsDialog(
            self._output_dir,
            self,
            language=self.language,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_output_dir(dialog.output_dir)
            self._set_language(dialog.language)

    def _set_output_dir(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._last_output_dir = output_dir
        self._preferences.setValue("output_dir", str(output_dir))

    def _set_language(self, language: object) -> None:
        normalized = normalize_language(language)
        if normalized == self.language:
            return
        self.language = normalized
        self._preferences.setValue("language", normalized)
        self.activity_log.clear()
        self._apply_language()
        self._append_log(self._t("log.language_changed"))

    def _apply_language(self) -> None:
        brand = self._t("app.brand")
        self.setWindowTitle(brand)
        self.brand_label.setText(brand)
        self.account_label.setText(self._t("sections.account"))
        self.export_label.setText(self._t("sections.export"))
        self.progress_label.setText(self._t("sections.progress"))
        self.activity_label.setText(self._t("sections.activity"))
        self.total_label.setText(self._t("metrics.total"))
        self.exported_label.setText(self._t("metrics.exported"))
        self.failed_label.setText(self._t("metrics.failed"))
        self.login_button.setText(self._t("buttons.login"))
        self.export_button.setText(self._t("buttons.start_export"))
        self.open_directory_button.setText(self._t("buttons.open_folder"))
        self.settings_button.setAccessibleName(self._t("buttons.open_settings"))
        self.settings_button.setToolTip(self._t("buttons.open_settings"))
        self.activity_log.setPlaceholderText(self._t("activity.placeholder"))
        self.header_status.setText(self._t(self._header_status_key))
        self.account_state.setText(
            self._t(self._account_state_key, **self._account_state_values),
        )
        self.current_item.setText(
            self._t(self._current_item_key, **self._current_item_values),
        )

        app = QApplication.instance()
        if app is not None:
            app.setApplicationDisplayName(brand)

    def _set_header_status(self, key: str) -> None:
        self._header_status_key = key
        self.header_status.setText(self._t(key))

    def _set_account_state(self, key: str, **values: object) -> None:
        self._account_state_key = key
        self._account_state_values = values
        self.account_state.setText(self._t(key, **values))

    def _set_current_item(self, key: str, **values: object) -> None:
        self._current_item_key = key
        self._current_item_values = values
        self.current_item.setText(self._t(key, **values))

    def _status_text(self, status: str) -> str:
        status_keys = {
            "已导出": "status.exported",
            "已存在": "status.existing",
            "失败": "status.failed",
        }
        key = status_keys.get(status)
        return self._t(key) if key is not None else status

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.appendPlainText(f"{timestamp}  {message}")

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(
            self,
            self._t("app.brand"),
            self._runtime_message(message),
        )

    def _runtime_message(self, message: str) -> str:
        return translate_runtime_message(self.language, message)

    def _restore_preferences(self) -> None:
        stored_path = self._preferences.value("output_dir", str(self.settings.output_dir))
        if stored_path:
            self._output_dir = Path(str(stored_path)).expanduser()
        geometry = self._preferences.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.warning(
                self,
                self._t("dialog.task_running.title"),
                self._t("dialog.task_running.body"),
            )
            event.ignore()
            return
        self._preferences.setValue("geometry", self.saveGeometry())
        event.accept()


def _rule() -> QFrame:
    line = QFrame()
    line.setObjectName("Rule")
    line.setFrameShape(QFrame.Shape.HLine)
    return line
