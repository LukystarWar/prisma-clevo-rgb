"""Small original glyph set for the effect picker, as inline SVG strings.

Rendered on demand via QtSvg so they can be recolored per state (dim when
unselected, neon green when checked) without shipping separate image
files. `{color}` is substituted before rendering.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STATIC = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <rect x="5" y="5" width="14" height="14" rx="3" fill="none" stroke="{color}" stroke-width="2"/>
  <rect x="9" y="9" width="6" height="6" rx="1.5" fill="{color}"/>
</svg>
"""

_RAINBOW = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M4 17 A8 8 0 0 1 20 17" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M7 17 A5 5 0 0 1 17 17" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" opacity="0.55"/>
  <circle cx="4" cy="17" r="1.4" fill="{color}"/>
  <circle cx="20" cy="17" r="1.4" fill="{color}"/>
</svg>
"""

_BREATHING = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="3" fill="{color}"/>
  <circle cx="12" cy="12" r="7" fill="none" stroke="{color}" stroke-width="1.6" opacity="0.5"/>
  <circle cx="12" cy="12" r="10.5" fill="none" stroke="{color}" stroke-width="1.4" opacity="0.25"/>
</svg>
"""

_OFF = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M12 4.5 V11" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
  <path d="M7.5 7 A7 7 0 1 0 16.5 7" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

TEMPLATES = {
    "static": _STATIC,
    "rainbow": _RAINBOW,
    "breathing": _BREATHING,
    "off": _OFF,
}


def make_icon(name: str, color: str, size: int = 22) -> QIcon:
    svg = TEMPLATES[name].format(color=color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(0x00000000)  # transparent (ARGB 0)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
