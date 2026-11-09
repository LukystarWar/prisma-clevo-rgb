"""Rasterizes assets/icon.svg into assets/icon.ico (multi-resolution).

Run after editing the SVG:
    .venv\\Scripts\\python.exe tools\\build_icon.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_APP = QGuiApplication(sys.argv)  # QPixmap/QPainter need a Qt application instance, even headless

ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "assets" / "icon.svg"
ICO_PATH = ROOT / "assets" / "icon.ico"
MASTER_SIZE = 256
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def render_png(size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(SVG_PATH.read_bytes()))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(0x00000000)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    return pixmap


def main() -> None:
    pixmap = render_png(MASTER_SIZE)
    tmp_png = ROOT / "assets" / "_icon_master.png"
    pixmap.save(str(tmp_png), "PNG")

    img = Image.open(tmp_png).convert("RGBA")
    img.save(ICO_PATH, format="ICO", sizes=ICO_SIZES)
    tmp_png.unlink()
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
