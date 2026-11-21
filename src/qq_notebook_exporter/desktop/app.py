from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from qq_notebook_exporter.desktop.main_window import MainWindow
from qq_notebook_exporter.desktop.style import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QQ 记事本导出")
    app.setOrganizationName("QQNotebookExporter")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
