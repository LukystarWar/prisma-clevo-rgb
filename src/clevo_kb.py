"""
Low-level control of the Clevo/Gigabyte keyboard RGB LEDs via InsydeDCHU.dll.

This reimplements, in Python, the exact calls the vendor's own app
(CLEVOCO.LedKeyboardSetting) makes through its CC.RGBKB / CC.InsydeAcpiProt
classes -- reverse engineered by dumping their IL (see docs/reference/).
Only the pieces needed by this project (zone colors + keyboard type) are
implemented; see CLAUDE.md for the parts that were deliberately left out
and why.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import IntEnum

DLL_PATH = r"C:\Program Files (x86)\ControlCenter\InsydeDCHU.dll"

# Clevo Kb_Type values the RGBKB class (and therefore this module) can drive.
# See CLAUDE.md "Zone & color encoding" for what changes if kbType is not in
# {6, 22} (there's a second, scaled color formula used by the other types).
SUPPORTED_KB_TYPES = (2, 6, 22)

CMD_SET_DATA = 103          # the one WMI/EC command used for every LED write
CMD_GET_INT = 70            # priming call GetKBType() makes before reading type
CMD_GET_BUFFER = 13         # buffer holding Kb_Type at offset 15


class Zone(IntEnum):
    """Part codes RGBKB::SetColor packs into bits 24-31 of the payload.

    CONFIRMED ON THIS HARDWARE (Kb_Type 6, Gigabyte G5 KC): only MID (0xF0)
    visibly changes the keyboard's color. LEFT (0x00) and RIGHT (0xF1),
    sent alone, are silent no-ops - verified repeatedly by sending each one
    by itself with the user watching the physical keyboard. This model has
    a single physical LED zone; the vendor software's 3-zone concept
    doesn't correspond to real hardware here. See CLAUDE.md.
    """
    LEFT = 0x00
    MID = 0xF0
    RIGHT = 0xF1


# The only part code proven to work on this hardware - use this for all writes.
WORKING_ZONE = Zone.MID


@dataclass(frozen=True)
class RGB:
    r: int
    g: int
    b: int

    def clamped(self) -> "RGB":
        return RGB(max(0, min(255, self.r)), max(0, min(255, self.g)), max(0, min(255, self.b)))


class KeyboardNotSupportedError(RuntimeError):
    pass


class ClevoKeyboard:
    """Thin ctypes wrapper. One instance per process - loads the DLL once."""

    def __init__(self) -> None:
        self._dll = ctypes.WinDLL(DLL_PATH)
        self._dll.GetDCHU_Data_Integer.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self._dll.GetDCHU_Data_Integer.restype = ctypes.c_int
        self._dll.GetDCHU_Data_Buffer.argtypes = [ctypes.c_int, ctypes.c_char_p]
        self._dll.GetDCHU_Data_Buffer.restype = ctypes.c_int
        self._dll.SetDCHU_Data.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self._dll.SetDCHU_Data.restype = ctypes.c_int
        self._kb_type: int | None = None

    def get_kb_type(self) -> int:
        """Mirrors BaseKB::GetKBType(): prime with GetDCHU_Data_Integer(70),
        then read byte 15 of the buffer returned by GetDCHU_Data_Buffer(13)."""
        if self._kb_type is not None:
            return self._kb_type
        scratch = ctypes.c_int(90)
        self._dll.GetDCHU_Data_Integer(CMD_GET_INT, ctypes.byref(scratch))
        buf = ctypes.create_string_buffer(4096)
        self._dll.GetDCHU_Data_Buffer(CMD_GET_BUFFER, buf)
        self._kb_type = buf.raw[15]
        return self._kb_type

    def assert_supported(self) -> None:
        kb_type = self.get_kb_type()
        if kb_type not in SUPPORTED_KB_TYPES:
            raise KeyboardNotSupportedError(
                f"Kb_Type {kb_type} is not one of the tested types {SUPPORTED_KB_TYPES}. "
                "Nothing was sent to the hardware."
            )

    def set_zone_color(self, zone: Zone, color: RGB) -> None:
        """Writes one zone's color. Confirmed visually on Kb_Type 6 for R/G/B
        primaries - see CLAUDE.md for the formula and how it was validated.

        NOTE: SetDCHU_Data's return value is NOT a success/error code (it was
        observed to just echo back the command id, 103, on every call during
        testing) - don't branch on it.
        """
        color = color.clamped()
        color_val = (color.b << 16) | (color.r << 8) | color.g
        payload = ((int(zone) << 24) + color_val) & 0xFFFFFFFF
        data = payload.to_bytes(4, "little")
        self._dll.SetDCHU_Data(CMD_SET_DATA, data, 4)

    def set_color(self, color: RGB) -> None:
        """Sets the keyboard's (single, physical) LED color. Use this instead
        of set_zone_color() unless you're specifically re-testing zone
        behavior - see WORKING_ZONE / Zone docstring above."""
        self.set_zone_color(WORKING_ZONE, color)
