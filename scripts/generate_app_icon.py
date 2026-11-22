from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QImage

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate app PNG and multi-size ICO assets.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    source = QImage(str(args.source))
    if source.isNull():
        raise SystemExit(f"Unable to read image: {args.source}")

    cropped = source.copy(_content_square(source))
    logo = cropped.scaled(
        512,
        512,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logo.save(str(args.output_dir / "app.png"), "PNG")

    png_frames = [
        (size, _png_bytes(cropped, size))
        for size in ICON_SIZES
    ]
    icon_path = args.output_dir / "app.ico"
    icon_path.write_bytes(_ico_bytes(png_frames))
    print(f"Wrote {args.output_dir / 'app.png'}")
    print(f"Wrote {icon_path}")
    return 0


def _content_square(image: QImage) -> QRect:
    probe = image.scaled(
        256,
        256,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    points = [
        (x, y)
        for y in range(probe.height())
        for x in range(probe.width())
        if _is_ink(probe.pixelColor(x, y))
    ]
    if not points:
        return QRect(0, 0, image.width(), image.height())

    left = min(x for x, _ in points)
    right = max(x for x, _ in points)
    top = min(y for _, y in points)
    bottom = max(y for _, y in points)
    scale_x = image.width() / probe.width()
    scale_y = image.height() / probe.height()
    center_x = int((left + right + 1) * scale_x / 2)
    center_y = int((top + bottom + 1) * scale_y / 2)
    content_size = int(max(right - left + 1, bottom - top + 1) * max(scale_x, scale_y))
    square_size = min(
        int(content_size * 1.08),
        image.width(),
        image.height(),
    )
    left_px = max(0, min(image.width() - square_size, center_x - square_size // 2))
    top_px = max(0, min(image.height() - square_size, center_y - square_size // 2))
    return QRect(left_px, top_px, square_size, square_size)


def _is_ink(color) -> bool:
    return min(color.red(), color.green(), color.blue()) < 235


def _png_bytes(image: QImage, size: int) -> bytes:
    scaled = image.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not scaled.save(buffer, "PNG"):
        raise SystemExit(f"Unable to encode {size}px icon")
    return bytes(buffer.data())


def _ico_bytes(frames: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = len(header) + len(frames) * 16
    entries = bytearray()
    payload = bytearray()
    for size, data in frames:
        dimension = 0 if size == 256 else size
        entries.extend(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        payload.extend(data)
        offset += len(data)
    return header + bytes(entries) + bytes(payload)


if __name__ == "__main__":
    raise SystemExit(main())
