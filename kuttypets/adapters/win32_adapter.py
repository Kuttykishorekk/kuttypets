"""
OmniPet - Windows 10/11 Win32 & DWM Window Adapter.
Tracks on-screen windows via DWM Extended Frame Bounds and integrates with GlazeWM/Komorebi.
"""

from __future__ import annotations
import sys
import ctypes
from typing import Dict, Any, List, Optional
from .base import BaseWindowAdapter, WindowInfo

class Win32Adapter(BaseWindowAdapter):
    """Windows Win32 API implementation using DWM Extended Frame Bounds (ignoring drop shadows and cloaked windows)."""

    def __init__(self):
        self._user32 = getattr(ctypes.windll, "user32", None)
        self._dwmapi = getattr(ctypes.windll, "dwmapi", None)
        self._init_dpi_awareness()

    def _init_dpi_awareness(self) -> None:
        """Sets Per-Monitor V2 DPI awareness so coordinates match display scale 1:1."""
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                if self._user32:
                    self._user32.SetProcessDPIAware()
            except Exception:
                pass

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

            # Ignore cloaked windows (Windows 10/11 virtual desktops & background UWP apps)
            DWMWA_CLOAKED = 14
            if self._dwmapi:
                cloaked = ctypes.c_int(0)
                if self._dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0:
                    if cloaked.value != 0:
                        return True

            # Check window class to ignore Desktop, Taskbar, and Overlay windows
            class_buf = ctypes.create_unicode_buffer(256)
            self._user32.GetClassNameW(hwnd, class_buf, 256)
            class_name = class_buf.value
            if class_name in (
                "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                "Windows.UI.Core.CoreWindow", "KuttyPetsOverlay", "Qt6QWindowIcon",
                "ApplicationFrameWindow", "tooltips_class32"
            ):
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

            # Filter out invalid, off-screen, or tiny windows
            if x1 < -200 or y1 < -200 or x1 > 25000 or y1 > 25000:
                return True
            if w < 140 or h < 140:
                return True

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
                app_class=class_name,
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
        # Windows 11 rounded corners and dynamic taskbar clearance via SPI_GETWORKAREA
        gap_bottom = 40.0
        gap_top = 0.0
        if self._user32:
            rect = (ctypes.c_long * 4)()
            SPI_GETWORKAREA = 0x0030
            if self._user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                screen_h = float(self._user32.GetSystemMetrics(1))
                gap_bottom = max(0.0, screen_h - float(rect[3]))
                gap_top = max(0.0, float(rect[1]))

        return {
            "rounding": 8.0,
            "border_size": 1.0,
            "gap_top": gap_top,
            "gap_bottom": gap_bottom,
        }
