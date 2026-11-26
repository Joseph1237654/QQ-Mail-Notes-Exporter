from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
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
        self._preferences = preferences or QSettings(
            "QQNotebookExporter",
            "QQMailNotebookExporter",
        )

        self.setWindowTitle("QQ 记事本导出")
        self.setWindowIcon(load_app_icon())
        self.setMinimumSize(QSize(900, 620))
        self.resize(1040, 720)
        self._build_ui()
        self._restore_preferences()
        self._apply_idle_state()

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
        logo.setAccessibleName("QQ 记事本导出图标")
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        brand = QLabel("QQ 记事本导出")
        brand.setObjectName("Brand")
        layout.addWidget(brand, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        self.header_status = QLabel("未登录")
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

        account_label = QLabel("账户")
        account_label.setObjectName("SectionLabel")
        layout.addWidget(account_label)

        self.account_state = QLabel("尚未登录")
        self.account_state.setObjectName("Muted")
        layout.addWidget(self.account_state)

        self.login_button = QPushButton("登录 QQ 邮箱")
        self.login_button.setObjectName("Primary")
        self.login_button.clicked.connect(self._start_login)
        layout.addWidget(self.login_button)

        layout.addWidget(_rule())
        export_label = QLabel("导出")
        export_label.setObjectName("SectionLabel")
        layout.addWidget(export_label)

        self.export_button = QPushButton("开始导出")
        self.export_button.setObjectName("Primary")
        self.export_button.clicked.connect(self._start_export)
        layout.addWidget(self.export_button)

        layout.addStretch(1)
        self.settings_button = QPushButton()
        self.settings_button.setObjectName("SettingsButton")
        self.settings_button.setIcon(settings_gear_icon())
        self.settings_button.setIconSize(QSize(27, 27))
        self.settings_button.setAccessibleName("打开设置")
        self.settings_button.setToolTip("打开设置")
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
        self.total_value = self._add_metric(metrics, "总计")
        self.exported_value = self._add_metric(metrics, "已导出")
        self.failed_value = self._add_metric(metrics, "失败")
        metrics.addStretch(1)
        layout.addLayout(metrics)
        layout.addWidget(_rule())

        progress_header = QHBoxLayout()
        progress_label = QLabel("进度")
        progress_label.setObjectName("SectionLabel")
        self.progress_percent = QLabel("0%")
        self.progress_percent.setObjectName("Muted")
        progress_header.addWidget(progress_label)
        progress_header.addStretch(1)
        progress_header.addWidget(self.progress_percent)
        layout.addLayout(progress_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.current_item = QLabel("等待开始")
        self.current_item.setObjectName("CurrentItem")
        self.current_item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.current_item)

        activity_header = QHBoxLayout()
        activity_label = QLabel("活动")
        activity_label.setObjectName("SectionLabel")
        self.open_directory_button = QPushButton("打开目录")
        self.open_directory_button.setObjectName("Ghost")
        self.open_directory_button.clicked.connect(self._open_output_directory)
        activity_header.addWidget(activity_label)
        activity_header.addStretch(1)
        activity_header.addWidget(self.open_directory_button)
        layout.addLayout(activity_header)

        self.activity_log = QPlainTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setPlaceholderText("导出记录会显示在这里")
        layout.addWidget(self.activity_log, 1)
        return content

    def _add_metric(self, layout: QHBoxLayout, label_text: str) -> QLabel:
        box = QVBoxLayout()
        box.setSpacing(0)
        value = QLabel("0")
        value.setObjectName("MetricValue")
        label = QLabel(label_text)
        label.setObjectName("MetricLabel")
        box.addWidget(value)
        box.addWidget(label)
        layout.addLayout(box)
        return value

    def _start_login(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._set_busy("等待登录")
        self.account_state.setText("等待浏览器登录")
        self.current_item.setText("请在 Edge 中完成登录")
        self._append_log("正在打开 QQ 邮箱登录窗口")

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
            self._append_log("请先完成 QQ 邮箱登录")
            return

        output_dir = self._output_dir
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._show_error(f"无法创建导出目录：{exc}")
            return

        self._last_output_dir = output_dir
        self._preferences.setValue("output_dir", str(output_dir))
        self._reset_progress()
        self._set_busy("正在导出")
        self._append_log(f"开始导出到 {output_dir}")

        worker = ExportWorker(self.settings, output_dir, parent=self)
        worker.progress.connect(self._update_progress)
        worker.succeeded.connect(self._export_succeeded)
        worker.failed.connect(self._task_failed)
        worker.finished.connect(self._worker_finished)
        self._worker = worker
        worker.start()

    def _login_succeeded(self, total: int) -> None:
        self._logged_in = True
        self.header_status.setText("已登录")
        self.account_state.setText(f"首屏可读取 {total} 条笔记")
        self.current_item.setText("登录态已验证")
        self._append_log(f"登录成功，首屏可读取 {total} 条笔记")
        self._apply_idle_state()

    def _export_succeeded(self, report: ExportReport) -> None:
        self.total_value.setText(str(report.total))
        self.exported_value.setText(str(report.exported))
        self.failed_value.setText(str(report.failed))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_percent.setText("100%")
        self.current_item.setText("导出完成")
        self.header_status.setText("已完成")
        self._last_output_dir = self._output_dir
        self._append_log(
            f"导出完成：{report.exported} 条成功，{report.skipped} 条跳过，"
            f"{report.failed} 条失败"
        )
        for failure in report.failures:
            self._append_log(f"失败 [{failure.note_id}] {failure.title}: {failure.message}")
        self._apply_idle_state()

    def _update_progress(self, index: int, total: int, status: str, title: str) -> None:
        percent = int(index * 100 / total) if total else 0
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        self.progress_percent.setText(f"{percent}%")
        self.total_value.setText(str(total))
        self.current_item.setText(f"{index} / {total} · {status} · {title}")
        if status == "失败":
            self._append_log(f"失败：{title}")

    def _task_failed(self, message: str) -> None:
        self.header_status.setText("出错")
        self.account_state.setText("任务失败")
        self.current_item.setText("任务失败")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._append_log(f"错误：{message}")
        self._show_error(message)
        self._apply_idle_state()

    def _worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._apply_idle_state()

    def _set_busy(self, status: str) -> None:
        self.header_status.setText(status)
        self.login_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_percent.setText("处理中")

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
        self.current_item.setText("准备读取记事本")

    def _open_output_directory(self) -> None:
        directory = self._last_output_dir or self._output_dir
        if directory.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    def _open_settings(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        dialog = SettingsDialog(self._output_dir, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_output_dir(dialog.output_dir)

    def _set_output_dir(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._last_output_dir = output_dir
        self._preferences.setValue("output_dir", str(output_dir))

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.appendPlainText(f"{timestamp}  {message}")

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "QQ 记事本导出", message)

    def _restore_preferences(self) -> None:
        stored_path = self._preferences.value("output_dir", str(self.settings.output_dir))
        if stored_path:
            self._output_dir = Path(str(stored_path)).expanduser()
        geometry = self._preferences.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.warning(self, "任务进行中", "请等待当前任务结束后再关闭窗口。")
            event.ignore()
            return
        self._preferences.setValue("geometry", self.saveGeometry())
        event.accept()


def _rule() -> QFrame:
    line = QFrame()
    line.setObjectName("Rule")
    line.setFrameShape(QFrame.Shape.HLine)
    return line
