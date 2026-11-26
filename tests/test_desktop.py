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
from qq_notebook_exporter.desktop.icon import app_logo_pixmap, settings_gear_icon  # noqa: E402
from qq_notebook_exporter.desktop.main_window import MainWindow  # noqa: E402
from qq_notebook_exporter.desktop.settings_dialog import SettingsDialog  # noqa: E402
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
        "QQNoteExporterTests",
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
    assert window.windowTitle() == "QQNoteExporter"
    assert not window.windowIcon().isNull()
    assert window.header_status.text() == "未登录"
    assert window.login_button.isEnabled()
    assert not window.export_button.isEnabled()
    assert window.settings_button.isEnabled()
    assert window.settings_button.text() == ""
    assert not window.settings_button.icon().isNull()
    assert window.settings_button.accessibleName() == "打开设置"
    assert window.settings_button.width() == 40
    assert window._output_dir.name == "exports"
    assert window.findChild(qt_widgets.QLabel, "BrandMeta") is None
    brand = window.findChild(qt_widgets.QLabel, "Brand")
    assert brand is not None
    assert brand.text() == "QQNoteExporter"
    logo = window.findChild(qt_widgets.QLabel, "AppIcon")
    assert logo is not None
    assert not logo.pixmap().isNull()


def test_brand_mark_uses_transparent_tinted_ink() -> None:
    image = app_logo_pixmap(40, "#D2D2D2").toImage()
    visible = [
        image.pixelColor(x, y)
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    ]

    assert image.pixelColor(0, 0).alpha() == 0
    assert visible
    assert all(color.red() == color.green() == color.blue() for color in visible)


def test_settings_gear_icon_has_transparent_center(app) -> None:
    image = settings_gear_icon().pixmap(64, 64).toImage()

    assert image.pixelColor(32, 32).alpha() == 0
    assert any(
        image.pixelColor(x, y).alpha() > 0
        for y in range(image.height())
        for x in range(image.width())
    )


def test_settings_directory_picker_updates_output_path(window, monkeypatch, tmp_path) -> None:
    selected = tmp_path / "selected-output"
    selected.mkdir()
    monkeypatch.setattr(
        qt_widgets.QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: str(selected),
    )

    dialog = SettingsDialog(window._output_dir, window)
    dialog._choose_directory()

    assert dialog.path_edit.text() == str(selected)


def test_settings_save_updates_main_window_output_path(window, tmp_path) -> None:
    selected = tmp_path / "settings-output"
    dialog = SettingsDialog(window._output_dir, window)
    dialog.path_edit.setText(str(selected))

    dialog._save()

    assert dialog.result() == qt_widgets.QDialog.DialogCode.Accepted
    window._set_output_dir(dialog.output_dir)
    assert window._output_dir == selected
    assert selected.is_dir()
    assert window._preferences.value("output_dir") == str(selected)


def test_about_page_contains_version_and_design_philosophy(window) -> None:
    dialog = SettingsDialog(window._output_dir, window)

    dialog.about_nav_button.click()

    version = dialog.findChild(qt_widgets.QLabel, "AboutVersion")
    philosophy = dialog.findChild(qt_widgets.QLabel, "AboutBody")
    assert dialog.pages.currentIndex() == 1
    assert version is not None
    assert version.text().startswith("版本 ")
    assert philosophy is not None
    assert "Word 文档" in philosophy.text()
    assert "本地优先" in philosophy.text()


def test_worker_finished_reenables_settings(window) -> None:
    class FinishedWorker:
        def deleteLater(self) -> None:
            pass

    window._logged_in = True
    window._set_busy("正在导出")
    assert not window.settings_button.isEnabled()

    window._worker = FinishedWorker()
    window._worker_finished()

    assert window._worker is None
    assert window.settings_button.isEnabled()
    assert window.export_button.isEnabled()


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
