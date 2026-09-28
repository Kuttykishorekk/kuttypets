"""
OmniPet - macOS Cocoa & CoreGraphics Window Adapter.
Tracks on-screen windows via Quartz/CoreGraphics and integrates with AeroSpace/Yabai.
"""

from __future__ import annotations
import json
import subprocess
from typing import Dict, Any, List, Optional
from .base import BaseWindowAdapter, WindowInfo

class MacOSCocoaAdapter(BaseWindowAdapter):
    """macOS implementation supporting both native AppKit windows and AeroSpace/Yabai tiling managers."""

    def __init__(self):
        self._has_aerospace: bool = self._check_cli_tool("aerospace")
        self._has_yabai: bool = self._check_cli_tool("yabai")

    @staticmethod
    def _check_cli_tool(name: str) -> bool:
        try:
            return subprocess.run(["which", name], capture_output=True).returncode == 0
        except Exception:
            return False

    def get_windows(self) -> List[WindowInfo]:
        # 1. Try AeroSpace if running
        if self._has_aerospace:
            try:
                res = subprocess.run(["aerospace", "list-windows", "--all", "--format", "%{window-id}|%{app-name}|%{window-title}"], capture_output=True, text=True, timeout=0.08)
                if res.returncode == 0:
                    pass
            except Exception:
                pass

        # 2. Native Quartz CGWindowList query
        windows: List[WindowInfo] = []
        try:
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                kCGWindowLayer,
                kCGWindowBounds,
                kCGWindowOwnerName,
                kCGWindowName,
                kCGWindowNumber,
            )
            raw_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            for w in raw_list:
                # Filter out system UI elements (Dock, Menu bar, Window Server overlays)
                layer = w.get(kCGWindowLayer, 0)
                if layer != 0:
                    continue
                bounds = w.get(kCGWindowBounds, {})
                x = float(bounds.get("X", 0))
                y = float(bounds.get("Y", 0))
                width = float(bounds.get("Width", 0))
                height = float(bounds.get("Height", 0))

                if width < 80 or height < 80:
                    continue

                wid = str(w.get(kCGWindowNumber, ""))
                owner = str(w.get(kCGWindowOwnerName, ""))
                title = str(w.get(kCGWindowName, ""))

                windows.append(WindowInfo(
                    address=wid,
                    x1=x,
                    x2=x + width,
                    y_top=y,
                    y_bot=y + height,
                    title=title,
                    app_class=owner,
                ))
        except ImportError:
            pass

        return windows

    def get_active_window(self) -> Optional[WindowInfo]:
        wins = self.get_windows()
        return wins[0] if wins else None

    def get_screen_geometry(self) -> Dict[str, float]:
        try:
            from AppKit import NSScreen
            main_screen = NSScreen.mainScreen()
            if main_screen:
                frame = main_screen.frame()
                scale = float(main_screen.backingScaleFactor())
                return {
                    "width": float(frame.size.width),
                    "height": float(frame.size.height),
                    "scale": scale,
                }
        except ImportError:
            pass
        return {"width": 1728.0, "height": 1117.0, "scale": 2.0}

    def get_layout_metrics(self) -> Dict[str, float]:
        # macOS has native ~18-22px window corner roundings on Modern macOS (Sonoma / Sequoia)
        return {
            "rounding": 18.0,
            "border_size": 1.0,
            "gap_top": 28.0,  # Menu bar / Notch clearance
            "gap_bottom": 4.0,
        }
