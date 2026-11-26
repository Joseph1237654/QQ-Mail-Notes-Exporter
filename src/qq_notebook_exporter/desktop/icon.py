from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap


def load_app_icon() -> QIcon:
    pixmap = app_logo_pixmap(256)
    if pixmap.isNull():
        return QIcon()
    return QIcon(pixmap)


def app_logo_pixmap(size: int, color: QColor | str | None = None) -> QPixmap:
    data = files("qq_notebook_exporter.resources").joinpath("app.png").read_bytes()
    pixmap = QPixmap()
    if not pixmap.loadFromData(data, "PNG"):
        return QPixmap()
    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if color is None:
        return scaled
    return _tint_ink(scaled, QColor(color))


def _tint_ink(pixmap: QPixmap, color: QColor) -> QPixmap:
    """Use the dark line work as a mask so the mark can sit on any background."""
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            source = image.pixelColor(x, y)
            ink = 255 - max(source.red(), source.green(), source.blue())
            alpha = ink * source.alpha() // 255
            if alpha == 0:
                image.setPixelColor(x, y, QColor(0, 0, 0, 0))
            else:
                image.setPixelColor(x, y, QColor(color.red(), color.green(), color.blue(), alpha))
    return QPixmap.fromImage(image)
