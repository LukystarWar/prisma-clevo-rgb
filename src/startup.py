"""Enable/disable launching this app automatically when Windows starts.

Uses the per-user Run key (HKCU) - no admin rights needed, unlike the
scheduled task in scheduled_task.py. When running from source (not the
PyInstaller build), registers pythonw.exe (no console window) + main.py;
when frozen, registers the .exe itself.
"""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Prisma"


def _command_line() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    interpreter = pythonw if pythonw.exists() else Path(sys.executable)
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{interpreter}" "{main_py}" --minimized'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def set_enabled(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command_line())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
