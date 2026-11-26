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
from qq_notebook_exporter.desktop.i18n import translate_runtime_message  # noqa: E402
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
    assert window.windowTitle() == "QQ邮箱记事本导出器"
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
    assert brand.text() == "QQ邮箱记事本导出器"
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
    dialog = SettingsDialog(window._output_dir, window, language=window.language)

    dialog.about_nav_button.click()

    version = dialog.findChild(qt_widgets.QLabel, "AboutVersion")
    philosophy = dialog.findChild(qt_widgets.QLabel, "AboutBody")
    assert dialog.pages.currentIndex() == 2
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


def test_language_setting_switches_entire_ui_to_english(window) -> None:
    window._set_language("en")
    app = QApplication.instance()
    assert app is not None

    assert window.windowTitle() == "QQ Mail Notebook Exporter"
    assert app.applicationDisplayName() == "QQ Mail Notebook Exporter"
    assert window.brand_label.text() == "QQ Mail Notebook Exporter"
    assert window.header_status.text() == "Not signed in"
    assert window.account_state.text() == "Not signed in"
    assert window.login_button.text() == "Sign in to QQ Mail"
    assert window.export_button.text() == "Start export"
    assert window.open_directory_button.text() == "Open folder"
    assert window.total_label.text() == "Total"
    assert window.exported_label.text() == "Exported"
    assert window.failed_label.text() == "Failed"
    assert window.current_item.text() == "Ready"
    assert window.activity_log.placeholderText() == "Export activity will appear here"
    assert window.settings_button.accessibleName() == "Open settings"
    assert window.settings_button.toolTip() == "Open settings"
    assert window._preferences.value("language") == "en"
    assert "Interface language changed to English." in window.activity_log.toPlainText()


def test_settings_language_page_saves_english(window, tmp_path) -> None:
    dialog = SettingsDialog(
        window._output_dir,
        window,
        language=window.language,
    )
    dialog.language_nav_button.click()

    assert dialog.pages.currentIndex() == 1
    assert dialog.language_combo.count() == 2
    dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("en"))
    dialog._save()

    assert dialog.result() == qt_widgets.QDialog.DialogCode.Accepted
    assert dialog.language == "en"

    window._set_output_dir(dialog.output_dir)
    window._set_language(dialog.language)
    assert window.brand_label.text() == "QQ Mail Notebook Exporter"


def test_settings_dialog_renders_english_copy(window) -> None:
    dialog = SettingsDialog(
        window._output_dir,
        window,
        language="en",
    )

    assert dialog.windowTitle() == "Settings"
    assert dialog.path_nav_button.text() == "Export path"
    assert dialog.language_nav_button.text() == "Language"
    assert dialog.about_nav_button.text() == "About"
    assert dialog.browse_button.text() == "Choose folder"
    assert dialog.cancel_button.text() == "Cancel"
    assert dialog.save_button.text() == "Save"

    dialog.about_nav_button.click()
    version = dialog.findChild(qt_widgets.QLabel, "AboutVersion")
    philosophy = dialog.findChild(qt_widgets.QLabel, "AboutBody")
    assert version is not None
    assert version.text().startswith("Version ")
    assert philosophy is not None
    assert "local-first" in philosophy.text()


def test_runtime_errors_follow_selected_language() -> None:
    assert (
        translate_runtime_message("en", "浏览器页面尚未初始化。")
        == "The browser page is not ready."
    )
    assert translate_runtime_message("en", "未知中文错误") == (
        "The task failed. Please try again."
    )
    assert translate_runtime_message("zh_CN", "浏览器页面尚未初始化。") == (
        "浏览器页面尚未初始化。"
    )


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
