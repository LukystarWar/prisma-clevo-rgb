"""Dark, neon-green visual theme for the app (Razer-software inspired).

Kept as plain data + one QSS string on purpose: swap COLORS to re-skin the
whole app without touching gui.py, and there is exactly one stylesheet to
read when something looks wrong.
"""
from __future__ import annotations

import ctypes

COLORS = {
    "bg_app": "#0A0A0B",
    "bg_panel": "#151517",
    "bg_panel_alt": "#1C1C1F",
    "bg_control": "#201F23",
    "border": "#2A2A2E",
    "border_soft": "#232327",
    "text_primary": "#ECECEE",
    "text_secondary": "#8D8D93",
    "text_dim": "#55555C",
    "accent": "#44D62C",
    "accent_strong": "#5CFF3B",
    "accent_dim": "#1F5E15",
    "danger": "#FF4545",
}

FONT_FAMILY = "Segoe UI"

QSS = f"""
* {{
    font-family: "{FONT_FAMILY}";
    color: {COLORS["text_primary"]};
}}

QMainWindow, #root {{
    background-color: {COLORS["bg_app"]};
}}

QLabel {{
    background: transparent;
}}

#appTitle {{
    font-size: 19px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {COLORS["text_primary"]};
}}

#appTitleAccent {{
    color: {COLORS["accent"]};
}}

#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {COLORS["text_secondary"]};
}}

#subtleLabel {{
    font-size: 11px;
    color: {COLORS["text_dim"]};
}}

#statusPillOk {{
    font-size: 11px;
    font-weight: 600;
    color: {COLORS["accent"]};
    background-color: rgba(68, 214, 44, 0.12);
    border: 1px solid {COLORS["accent_dim"]};
    border-radius: 9px;
    padding: 3px 10px;
}}

#statusPillError {{
    font-size: 11px;
    font-weight: 600;
    color: {COLORS["danger"]};
    background-color: rgba(255, 69, 69, 0.10);
    border: 1px solid rgba(255, 69, 69, 0.35);
    border-radius: 9px;
    padding: 3px 10px;
}}

#card {{
    background-color: {COLORS["bg_panel"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 10px;
}}

QToolButton#effectPill {{
    background-color: {COLORS["bg_control"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 10px 6px;
    color: {COLORS["text_secondary"]};
    font-size: 12px;
    font-weight: 600;
}}

QToolButton#effectPill:hover {{
    border: 1px solid {COLORS["text_dim"]};
    color: {COLORS["text_primary"]};
}}

QToolButton#effectPill:checked {{
    background-color: rgba(68, 214, 44, 0.10);
    border: 1px solid {COLORS["accent"]};
    color: {COLORS["accent_strong"]};
}}

QToolButton#effectPill:disabled {{
    color: {COLORS["text_dim"]};
    border: 1px solid {COLORS["border_soft"]};
}}

QPushButton#ghostButton {{
    background-color: transparent;
    border: 1px solid {COLORS["border"]};
    border-radius: 7px;
    padding: 7px 14px;
    color: {COLORS["text_primary"]};
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#ghostButton:hover {{
    border: 1px solid {COLORS["accent"]};
    color: {COLORS["accent_strong"]};
}}

QPushButton#ghostButton:pressed {{
    background-color: rgba(68, 214, 44, 0.08);
}}

#hexLabel {{
    font-family: "Consolas";
    font-size: 13px;
    font-weight: 600;
    color: {COLORS["text_primary"]};
    letter-spacing: 1px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {COLORS["border"]};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {COLORS["accent"]};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: {COLORS["text_primary"]};
    border: 2px solid {COLORS["accent"]};
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS["accent_strong"]};
}}

QSlider:disabled::groove:horizontal {{
    background: {COLORS["border_soft"]};
}}

QSlider:disabled::sub-page:horizontal {{
    background: {COLORS["text_dim"]};
}}

QSlider:disabled::handle:horizontal {{
    background: {COLORS["text_dim"]};
    border: 2px solid {COLORS["border"]};
}}

QToolTip {{
    background-color: {COLORS["bg_panel_alt"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    padding: 4px 8px;
}}
"""


def enable_dark_titlebar(window) -> None:
    """Best-effort: ask DWM to paint this window's native title bar dark.
    No-op (silently) on anything older than Windows 10 20H1 or if it fails -
    this is a cosmetic touch, never worth crashing the app over."""
    try:
        hwnd = int(window.winId())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass
