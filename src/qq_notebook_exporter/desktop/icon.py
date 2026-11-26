from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)


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


def settings_gear_icon(size: int = 64, color: QColor | str = "#686868") -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(
        QColor(color),
        size * 0.0625,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin,
    )
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    center = size / 2
    core_radius = size * 0.245
    outer_radius = size * 0.405
    tooth_width = size * 0.145
    tooth_length = outer_radius - core_radius + size * 0.03

    gear = QPainterPath()
    gear.addEllipse(QPointF(center, center), core_radius, core_radius)
    for index in range(8):
        tooth = QPainterPath()
        tooth.addRoundedRect(
            QRectF(
                -tooth_width / 2,
                -outer_radius,
                tooth_width,
                tooth_length,
            ),
            tooth_width / 2,
            tooth_width / 2,
        )
        transform = QTransform()
        transform.translate(center, center)
        transform.rotate(index * 45)
        gear = gear.united(transform.map(tooth))

    painter.drawPath(gear)
    painter.drawEllipse(QPointF(center, center), size * 0.12, size * 0.12)
    painter.end()
    return QIcon(pixmap)
