"""Small custom widgets the default Qt set doesn't give a premium look for."""
from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QCheckBox

from theme import COLORS


class ToggleSwitch(QCheckBox):
    """An iOS/Synapse-style sliding toggle, built on QCheckBox so all the
    normal checked/toggled/isChecked API still works - only paintEvent and
    sizeHint differ from a regular checkbox."""

    WIDTH, HEIGHT = 40, 22

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._thumb_pos = 2.0
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        end = self.WIDTH - self.HEIGHT + 2 if checked else 2.0
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(float(end))
        self._anim.start()

    def getThumbPos(self) -> float:
        return self._thumb_pos

    def setThumbPos(self, value: float) -> None:
        self._thumb_pos = value
        self.update()

    thumbPos = Property(float, getThumbPos, setThumbPos)

    def sizeHint(self):
        from PySide6.QtCore import QSize

        return QSize(self.WIDTH, self.HEIGHT)

    def hitButton(self, pos) -> bool:  # noqa: N802 (Qt override)
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        track_rect = QRectF(0, 0, self.WIDTH, self.HEIGHT)
        track_color = QColor(COLORS["accent"]) if self.isChecked() else QColor(COLORS["border"])
        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, self.HEIGHT / 2, self.HEIGHT / 2)

        thumb_d = self.HEIGHT - 4
        painter.setBrush(QColor(COLORS["text_primary"]))
        painter.drawEllipse(QRectF(self._thumb_pos, 2, thumb_d, thumb_d))
        painter.end()
