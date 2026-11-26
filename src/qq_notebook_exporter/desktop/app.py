from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from qq_notebook_exporter.desktop.icon import load_app_icon
from qq_notebook_exporter.desktop.main_window import MainWindow
from qq_notebook_exporter.desktop.style import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QQNoteExporter")
    app.setApplicationDisplayName("QQNoteExporter")
    app.setOrganizationName("QQNoteExporter")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    app.setWindowIcon(load_app_icon())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
