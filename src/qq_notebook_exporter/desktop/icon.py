from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap


def load_app_icon() -> QIcon:
    pixmap = app_logo_pixmap(256)
    if pixmap.isNull():
        return QIcon()
    return QIcon(pixmap)


def app_logo_pixmap(size: int) -> QPixmap:
    data = files("qq_notebook_exporter.resources").joinpath("app.png").read_bytes()
    pixmap = QPixmap()
    if not pixmap.loadFromData(data, "PNG"):
        return QPixmap()
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
