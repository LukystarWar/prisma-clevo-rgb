"""Pure math for the animated effects. No hardware/Qt imports here on purpose,
so these functions are trivial to unit-test or tweak without touching the GUI."""
from __future__ import annotations

import math

from clevo_kb import RGB


def hue_to_rgb(hue_degrees: float) -> RGB:
    """Full-saturation, full-value HSV -> RGB. Same formula used by the
    scheduled-task script (scripts/ColorCycle.ps1) for the rainbow effect."""
    h = hue_degrees % 360
    x = 1 - abs((h / 60) % 2 - 1)
    sector = int(h // 60)
    if sector == 0:
        r, g, b = 1, x, 0
    elif sector == 1:
        r, g, b = x, 1, 0
    elif sector == 2:
        r, g, b = 0, 1, x
    elif sector == 3:
        r, g, b = 0, x, 1
    elif sector == 4:
        r, g, b = x, 0, 1
    else:
        r, g, b = 1, 0, x
    return RGB(round(r * 255), round(g * 255), round(b * 255))


def breathing_scale(phase_degrees: float) -> float:
    """0..1 brightness multiplier, smooth in/out (cosine), for the breathing effect."""
    return (1 - math.cos(math.radians(phase_degrees % 360))) / 2


def scale_rgb(color: RGB, factor: float) -> RGB:
    return RGB(round(color.r * factor), round(color.g * factor), round(color.b * factor)).clamped()
