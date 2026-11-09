"""Pause/resume the 'KeyboardColorCycle' scheduled task (scripts/ColorCycle.ps1).

That task writes to the same LED zones this app controls, in an infinite loop,
so the two must never run at the same time (see CLAUDE.md "Known conflict").
Ending/disabling a SYSTEM-level task normally requires an elevated process;
callers should expect PermissionError and tell the user to run as admin.
"""
from __future__ import annotations

import subprocess

TASK_NAME = "KeyboardColorCycle"
_CREATE_NO_WINDOW = 0x08000000


def _run(*args: str) -> None:
    result = subprocess.run(
        ["schtasks.exe", *args],
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        raise PermissionError(
            f"{' '.join(args)} failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )


def pause() -> None:
    _run("/End", "/TN", TASK_NAME)
    _run("/Change", "/TN", TASK_NAME, "/DISABLE")


def resume() -> None:
    _run("/Change", "/TN", TASK_NAME, "/ENABLE")
    _run("/Run", "/TN", TASK_NAME)
