from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
qt_widgets = pytest.importorskip("PySide6.QtWidgets")
qt_core = pytest.importorskip("PySide6.QtCore")
qt_gui = pytest.importorskip("PySide6.QtGui")

QApplication = qt_widgets.QApplication
QSettings = qt_core.QSettings
QColor = qt_gui.QColor

from qq_notebook_exporter.config import Settings  # noqa: E402
from qq_notebook_exporter.desktop.main_window import MainWindow  # noqa: E402
from qq_notebook_exporter.desktop.style import APP_STYLE  # noqa: E402
from qq_notebook_exporter.workflow import ExportFailure, ExportReport  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    application.setStyleSheet(APP_STYLE)
    yield application


@pytest.fixture
def window(app, tmp_path):
    settings = Settings(
        output_dir=tmp_path / "exports",
        profile_dir=tmp_path / "profile" / "browser",
        login_timeout=1,
    )
    preferences = QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        "QQNotebookExporterTests",
        f"test-{tmp_path.name}",
    )
    preferences.clear()
    window = MainWindow(settings, preferences)
    window.show()
    app.processEvents()
    yield window
    window.close()
    preferences.clear()


def test_initial_window_state(window) -> None:
    assert window.windowTitle() == "QQ 记事本导出"
    assert not window.windowIcon().isNull()
    assert window.header_status.text() == "未登录"
    assert window.login_button.isEnabled()
    assert not window.export_button.isEnabled()
    assert window.path_edit.text().endswith("exports")
    logo = window.findChild(qt_widgets.QLabel, "AppIcon")
    assert logo is not None
    assert not logo.pixmap().isNull()


def test_login_progress_and_export_result(window, app) -> None:
    window._login_succeeded(24)
    assert window.header_status.text() == "已登录"
    assert window.export_button.isEnabled()

    window._update_progress(3, 12, "已导出", "项目周记")
    app.processEvents()
    assert window.total_value.text() == "12"
    assert window.progress_bar.value() == 25
    assert "项目周记" in window.current_item.text()

    report = ExportReport(
        total=12,
        exported=11,
        skipped=0,
        failures=[ExportFailure("_9", "失败笔记", "正文缺失")],
    )
    window._export_succeeded(report)
    app.processEvents()

    assert window.exported_value.text() == "11"
    assert window.failed_value.text() == "1"
    assert window.progress_bar.value() == 100
    assert "正文缺失" in window.activity_log.toPlainText()


def test_ui_renders_black_white_and_gray_regions(window, app) -> None:
    app.processEvents()
    image = window.grab().toImage()

    assert image.width() >= 900
    assert image.height() >= 620
    assert _is_near(image.pixelColor(20, 20), QColor("#111111"))
    assert _is_near(image.pixelColor(20, 120), QColor("#FAFAFA"))
    assert _is_near(image.pixelColor(500, 120), QColor("#F2F2F2"))


def _is_near(actual: QColor, expected: QColor, tolerance: int = 8) -> bool:
    return all(
        (
            abs(actual.red() - expected.red()) <= tolerance,
            abs(actual.green() - expected.green()) <= tolerance,
            abs(actual.blue() - expected.blue()) <= tolerance,
        )
    )
