"""
OmniPet - Windows 10/11 Win32 & DWM Window Adapter.
Tracks on-screen windows via DWM Extended Frame Bounds and integrates with GlazeWM/Komorebi.
"""

from __future__ import annotations
import ctypes
from typing import Dict, Any, List, Optional
from .base import BaseWindowAdapter, WindowInfo

class Win32Adapter(BaseWindowAdapter):
    """Windows Win32 API implementation using DWM Extended Frame Bounds (ignoring drop shadows)."""

    def __init__(self):
        self._user32 = getattr(ctypes.windll, "user32", None)
        self._dwmapi = getattr(ctypes.windll, "dwmapi", None)

    def get_windows(self) -> List[WindowInfo]:
        windows: List[WindowInfo] = []
        if not self._user32:
            return windows

        def _enum_proc(hwnd, _lparam):
            if not self._user32.IsWindowVisible(hwnd):
                return True
            # Ignore minimized windows
            if self._user32.IsIconic(hwnd):
                return True

            # Use DwmGetWindowAttribute to get accurate client rect without invisible drop shadow margins
            rect = (ctypes.c_long * 4)()
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            if self._dwmapi and self._dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)) == 0:
                x1, y1, x2, y2 = rect[0], rect[1], rect[2], rect[3]
            else:
                raw_rect = (ctypes.c_long * 4)()
                self._user32.GetWindowRect(hwnd, ctypes.byref(raw_rect))
                x1, y1, x2, y2 = raw_rect[0], raw_rect[1], raw_rect[2], raw_rect[3]

            w = x2 - x1
            h = y2 - y1
            if w > 100 and h > 100:
                length = self._user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                self._user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

                windows.append(WindowInfo(
                    address=str(hwnd),
                    x1=float(x1),
                    x2=float(x2),
                    y_top=float(y1),
                    y_bot=float(y2),
                    title=title,
                ))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        self._user32.EnumWindows(WNDENUMPROC(_enum_proc), 0)
        return windows

    def get_active_window(self) -> Optional[WindowInfo]:
        if not self._user32:
            return None
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None
        rect = (ctypes.c_long * 4)()
        self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return WindowInfo(
            address=str(hwnd),
            x1=float(rect[0]),
            x2=float(rect[2]),
            y_top=float(rect[1]),
            y_bot=float(rect[3]),
            is_active=True,
        )

    def get_screen_geometry(self) -> Dict[str, float]:
        if self._user32:
            w = float(self._user32.GetSystemMetrics(0))
            h = float(self._user32.GetSystemMetrics(1))
            return {"width": w, "height": h, "scale": 1.0}
        return {"width": 1920.0, "height": 1080.0, "scale": 1.0}

    def get_layout_metrics(self) -> Dict[str, float]:
        # Windows 11 has 8px rounded corners and 40px taskbar at bottom
        return {
            "rounding": 8.0,
            "border_size": 1.0,
            "gap_top": 0.0,
            "gap_bottom": 40.0,  # Taskbar clearance
        }
