from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
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
from qq_notebook_exporter.desktop.icon import app_logo_pixmap, load_app_icon


class SettingsDialog(QDialog):
    def __init__(self, output_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.output_dir = output_dir
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("设置")
        self.setWindowIcon(load_app_icon())
        self.setModal(True)
        self.setMinimumSize(720, 500)
        self.resize(780, 540)
        self._build_ui()

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

        title = QLabel("设置")
        title.setObjectName("SettingsNavTitle")
        layout.addWidget(title)

        subtitle = QLabel("QQ 记事本导出")
        subtitle.setObjectName("SettingsNavSubtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.path_nav_button = self._add_nav_button(layout, "导出路径", 0)
        self.about_nav_button = self._add_nav_button(layout, "关于我们", 1)
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
        self.close_button = QPushButton("关闭")
        self.close_button.setObjectName("Ghost")
        self.close_button.setAutoDefault(False)
        self.close_button.setToolTip("关闭设置")
        self.close_button.clicked.connect(self.reject)
        header.addWidget(self.page_title)
        header.addStretch(1)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_path_page())
        self.pages.addWidget(self._build_about_page())
        layout.addWidget(self.pages, 1)
        return panel

    def _build_path_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        description = QLabel("设置 Word 文档的保存位置。每条笔记会生成一个独立文件。")
        description.setObjectName("SettingsDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        path_label = QLabel("保存位置")
        path_label.setObjectName("SectionLabel")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit(str(self.output_dir))
        self.path_edit.setPlaceholderText("选择 Word 导出目录")
        self.path_edit.setAccessibleName("导出路径")
        self.path_edit.setClearButtonEnabled(True)
        self.path_edit.setToolTip(str(self.output_dir))
        self.browse_button = QPushButton("选择目录")
        self.browse_button.setMinimumWidth(100)
        self.browse_button.setToolTip("选择 Word 文件的保存位置")
        self.browse_button.setAutoDefault(False)
        self.browse_button.clicked.connect(self._choose_directory)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_button)
        layout.addLayout(path_row)

        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("Primary")
        self.save_button.setDefault(True)
        self.save_button.setToolTip("保存导出路径")
        self.save_button.clicked.connect(self._save)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
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
        logo.setAccessibleName("QQ 记事本导出图标")
        identity.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)

        identity_text = QVBoxLayout()
        identity_text.setSpacing(3)
        name = QLabel("QQ 记事本导出")
        name.setObjectName("AboutName")
        version = QLabel(f"版本 {__version__}")
        version.setObjectName("AboutVersion")
        identity_text.addWidget(name)
        identity_text.addWidget(version)
        identity_text.addStretch(1)
        identity.addLayout(identity_text, 1)
        layout.addLayout(identity)

        tagline = QLabel("让散落的个人记录被妥善保存。")
        tagline.setObjectName("AboutTagline")
        layout.addWidget(tagline)
        layout.addWidget(_rule())

        philosophy_label = QLabel("设计理念")
        philosophy_label.setObjectName("SectionLabel")
        layout.addWidget(philosophy_label)

        philosophy = QLabel(
            "把散落在 QQ 邮箱记事本里的个人记录，整理成可长期保存、便于检索和迁移的"
            " Word 文档。软件坚持本地优先，不接收或保存 QQ 密码，导出结果只写入用户"
            "指定的目录。界面保持克制，流程尽量直接，让每一次导出都清晰、可预期。"
        )
        philosophy.setObjectName("AboutBody")
        philosophy.setWordWrap(True)
        philosophy.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(philosophy)
        layout.addStretch(1)
        return page

    def _show_page(self, index: int) -> None:
        titles = ("导出路径", "关于我们")
        self.pages.setCurrentIndex(index)
        self.page_title.setText(titles[index])
        self.nav_group.button(index).setChecked(True)

    def _choose_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择 Word 导出目录",
            self.path_edit.text() or str(self.output_dir),
        )
        if directory:
            self.path_edit.setText(directory)
            self.path_edit.setCursorPosition(0)
            self.path_edit.setToolTip(directory)

    def _save(self) -> None:
        value = self.path_edit.text().strip()
        if not value:
            QMessageBox.warning(self, "导出路径", "请先选择 Word 导出目录。")
            return

        output_dir = Path(value).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "导出路径", f"无法使用该目录：{exc}")
            return

        self.output_dir = output_dir
        self.accept()


def _rule() -> QFrame:
    line = QFrame()
    line.setObjectName("Rule")
    line.setFrameShape(QFrame.Shape.HLine)
    return line
