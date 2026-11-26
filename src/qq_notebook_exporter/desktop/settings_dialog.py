from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from qq_notebook_exporter import __version__
from qq_notebook_exporter.desktop.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    normalize_language,
    translate,
)
from qq_notebook_exporter.desktop.icon import app_logo_pixmap, load_app_icon


class SettingsDialog(QDialog):
    def __init__(
        self,
        output_dir: Path,
        parent: QWidget | None = None,
        *,
        language: object = DEFAULT_LANGUAGE,
    ) -> None:
        super().__init__(parent)
        self.output_dir = output_dir
        self.language = normalize_language(language)
        self.setObjectName("SettingsDialog")
        self.setWindowTitle(self._t("settings.window_title"))
        self.setWindowIcon(load_app_icon())
        self.setModal(True)
        self.setMinimumSize(720, 500)
        self.resize(780, 540)
        self._build_ui()

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_navigation())
        root.addWidget(self._build_panel(), 1)
        self._show_page(0)

    def _build_navigation(self) -> QFrame:
        navigation = QFrame()
        navigation.setObjectName("SettingsNav")
        navigation.setFixedWidth(190)
        layout = QVBoxLayout(navigation)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(8)

        title = QLabel(self._t("settings.title"))
        title.setObjectName("SettingsNavTitle")
        layout.addWidget(title)

        subtitle = QLabel(self._t("app.brand"))
        subtitle.setObjectName("SettingsNavSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.path_nav_button = self._add_nav_button(layout, self._t("settings.nav.path"), 0)
        self.language_nav_button = self._add_nav_button(
            layout,
            self._t("settings.nav.language"),
            1,
        )
        self.about_nav_button = self._add_nav_button(layout, self._t("settings.nav.about"), 2)
        self.nav_group.idClicked.connect(self._show_page)

        layout.addStretch(1)
        return navigation

    def _add_nav_button(self, layout: QVBoxLayout, text: str, index: int) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("SettingsNavItem")
        button.setCheckable(True)
        button.setAutoDefault(False)
        self.nav_group.addButton(button, index)
        layout.addWidget(button)
        return button

    def _build_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        self.page_title = QLabel()
        self.page_title.setObjectName("SettingsPageTitle")
        self.close_button = QPushButton(self._t("settings.close"))
        self.close_button.setObjectName("Ghost")
        self.close_button.setAutoDefault(False)
        self.close_button.setToolTip(self._t("settings.close_tooltip"))
        self.close_button.clicked.connect(self.reject)
        header.addWidget(self.page_title)
        header.addStretch(1)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_path_page())
        self.pages.addWidget(self._build_language_page())
        self.pages.addWidget(self._build_about_page())
        layout.addWidget(self.pages, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_button = QPushButton(self._t("buttons.cancel"))
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton(self._t("buttons.save"))
        self.save_button.setObjectName("Primary")
        self.save_button.setDefault(True)
        self.save_button.setToolTip(self._t("settings.save_tooltip"))
        self.save_button.clicked.connect(self._save)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
        return panel

    def _build_path_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        description = QLabel(self._t("settings.path.description"))
        description.setObjectName("SettingsDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        path_label = QLabel(self._t("settings.path.label"))
        path_label.setObjectName("SectionLabel")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit(str(self.output_dir))
        self.path_edit.setPlaceholderText(self._t("settings.path.placeholder"))
        self.path_edit.setAccessibleName(self._t("settings.path.accessible"))
        self.path_edit.setClearButtonEnabled(True)
        self.path_edit.setToolTip(str(self.output_dir))
        self.browse_button = QPushButton(self._t("settings.choose_directory"))
        self.browse_button.setMinimumWidth(100)
        self.browse_button.setToolTip(self._t("settings.choose_directory_tooltip"))
        self.browse_button.setAutoDefault(False)
        self.browse_button.clicked.connect(self._choose_directory)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_button)
        layout.addLayout(path_row)

        layout.addStretch(1)
        return page

    def _build_language_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        description = QLabel(self._t("settings.language.description"))
        description.setObjectName("SettingsDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        language_label = QLabel(self._t("settings.language.label"))
        language_label.setObjectName("SectionLabel")
        layout.addWidget(language_label)

        self.language_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(label, code)
        current_index = self.language_combo.findData(self.language)
        self.language_combo.setCurrentIndex(max(0, current_index))
        self.language_combo.setAccessibleName(self._t("settings.language.label"))
        layout.addWidget(self.language_combo)

        hint = QLabel(self._t("settings.language.hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        identity = QHBoxLayout()
        identity.setSpacing(14)
        logo = QLabel()
        logo.setObjectName("AboutIcon")
        logo.setFixedSize(54, 54)
        logo.setPixmap(app_logo_pixmap(54, "#222222"))
        logo.setAccessibleName(self._t("app.icon_accessible"))
        identity.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)

        identity_text = QVBoxLayout()
        identity_text.setSpacing(3)
        name = QLabel(self._t("app.brand"))
        name.setObjectName("AboutName")
        version = QLabel(self._t("settings.version", version=__version__))
        version.setObjectName("AboutVersion")
        identity_text.addWidget(name)
        identity_text.addWidget(version)
        identity_text.addStretch(1)
        identity.addLayout(identity_text, 1)
        layout.addLayout(identity)

        tagline = QLabel(self._t("settings.tagline"))
        tagline.setObjectName("AboutTagline")
        layout.addWidget(tagline)
        layout.addWidget(_rule())

        philosophy_label = QLabel(self._t("settings.philosophy_title"))
        philosophy_label.setObjectName("SectionLabel")
        layout.addWidget(philosophy_label)

        philosophy = QLabel(self._t("settings.philosophy_body"))
        philosophy.setObjectName("AboutBody")
        philosophy.setWordWrap(True)
        philosophy.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(philosophy)
        layout.addStretch(1)
        return page

    def _show_page(self, index: int) -> None:
        titles = (
            self._t("settings.nav.path"),
            self._t("settings.nav.language"),
            self._t("settings.nav.about"),
        )
        self.pages.setCurrentIndex(index)
        self.page_title.setText(titles[index])
        self.nav_group.button(index).setChecked(True)

    def _choose_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            self._t("filedialog.choose_word_dir"),
            self.path_edit.text() or str(self.output_dir),
        )
        if directory:
            self.path_edit.setText(directory)
            self.path_edit.setCursorPosition(0)
            self.path_edit.setToolTip(directory)

    def _save(self) -> None:
        value = self.path_edit.text().strip()
        if not value:
            QMessageBox.warning(
                self,
                self._t("settings.path_required_title"),
                self._t("settings.path_required_message"),
            )
            return

        output_dir = Path(value).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(
                self,
                self._t("settings.path_required_title"),
                self._t("settings.invalid_dir_message", error=exc),
            )
            return

        self.output_dir = output_dir
        self.language = normalize_language(self.language_combo.currentData())
        self.accept()


def _rule() -> QFrame:
    line = QFrame()
    line.setObjectName("Rule")
    line.setFrameShape(QFrame.Shape.HLine)
    return line
