"""
OmniPet - Linux Hyprland & Wayland Window Adapter.
Uses zero-latency direct UNIX domain sockets for client queries and compositor event streams.
"""

from __future__ import annotations
import os
import json
import socket
import threading
from typing import Dict, Any, List, Optional, Callable
from .base import BaseWindowAdapter, WindowInfo

class LinuxHyprlandAdapter(BaseWindowAdapter):
    """Hyprland compositor IPC implementation."""

    def __init__(self):
        self.signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
        self.xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", "")
        self.socket_path = ""
        self.socket2_path = ""
        self._init_socket_paths()
        self._event_thread: Optional[threading.Thread] = None

    def _init_socket_paths(self) -> None:
        if not self.signature or not self.xdg_runtime:
            return
        base = os.path.join(self.xdg_runtime, "hypr", self.signature)
        self.socket_path = os.path.join(base, ".socket.sock")
        self.socket2_path = os.path.join(base, ".socket2.sock")

    def _query(self, command: str) -> Optional[Any]:
        if not self.socket_path or not os.path.exists(self.socket_path):
            return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.04)
                s.connect(self.socket_path)
                s.sendall(f"j/{command}".encode())
                buf = bytearray()
                while True:
                    chunk = s.recv(16384)
                    if not chunk:
                        break
                    buf.extend(chunk)
                return json.loads(buf.decode("utf-8", errors="ignore"))
        except Exception:
            return None

    def get_windows(self) -> List[WindowInfo]:
        clients = self._query("clients")
        active_ws_data = self._query("activeworkspace")
        mons = self._query("monitors")

        if not clients:
            return []

        active_ws_id = active_ws_data.get("id", 1) if active_ws_data else 1
        special_ws_id = mons[0].get("specialWorkspace", {}).get("id", 0) if (mons and isinstance(mons, list)) else 0

        scale = float(mons[0].get("scale", 1.0)) if (mons and isinstance(mons, list)) else 1.0
        windows: List[WindowInfo] = []

        for c in clients:
            if not c.get("mapped") or c.get("hidden"):
                continue
            c_ws = c.get("workspace", {}).get("id")
            if c_ws == active_ws_id or (special_ws_id != 0 and c_ws == special_ws_id):
                ax, ay = c.get("at", [0, 0])
                aw, ah = c.get("size", [0, 0])
                if aw > 60 and ah > 60:
                    windows.append(WindowInfo(
                        address=str(c.get("address", "")),
                        x1=float(ax),
                        x2=float(ax + aw),
                        y_top=float(ay),
                        y_bot=float(ay + ah),
                        title=str(c.get("title", "")),
                        app_class=str(c.get("class", "")),
                        is_floating=bool(c.get("floating", False)),
                    ))
        return windows

    def get_active_window(self) -> Optional[WindowInfo]:
        aw = self._query("activewindow")
        if not aw or not aw.get("mapped") or aw.get("hidden"):
            return None
        
        ax, ay = aw.get("at", [0, 0])
        aw_w, aw_h = aw.get("size", [0, 0])
        return WindowInfo(
            address=str(aw.get("address", "")),
            x1=float(ax),
            x2=float(ax + aw_w),
            y_top=float(ay),
            y_bot=float(ay + aw_h),
            title=str(aw.get("title", "")),
            app_class=str(aw.get("class", "")),
            is_active=True,
            is_floating=bool(aw.get("floating", False)),
        )

    def get_screen_geometry(self) -> Dict[str, float]:
        mons = self._query("monitors")
        if mons and isinstance(mons, list):
            m = mons[0]
            scale = float(m.get("scale", 1.0)) or 1.0
            return {
                "width": float(m.get("width", 1920)) / scale,
                "height": float(m.get("height", 1080)) / scale,
                "scale": scale,
            }
        return {"width": 1920.0, "height": 1080.0, "scale": 1.0}

    def get_layout_metrics(self) -> Dict[str, float]:
        rounding = 24.0
        border_size = 2.0
        gap_top = 8.0
        gap_bottom = 0.0

        try:
            r_data = self._query("getoption decoration:rounding")
            if r_data and "int" in r_data:
                rounding = max(0.0, float(r_data["int"]))
            b_data = self._query("getoption general:border_size")
            if b_data and "int" in b_data:
                border_size = max(1.0, float(b_data["int"]))
        except Exception:
            pass

        return {
            "rounding": rounding,
            "border_size": border_size,
            "gap_top": gap_top,
            "gap_bottom": gap_bottom,
        }

    def start_event_listener(self, on_change_callback: Callable[[], None]) -> None:
        if not self.socket2_path or not os.path.exists(self.socket2_path):
            return

        def _worker():
            while True:
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.connect(self.socket2_path)
                        while True:
                            data = s.recv(2048).decode(errors="ignore")
                            if not data:
                                break
                            events = ["activewindow", "movewindow", "resizewindow", "openwindow", "closewindow", "workspace"]
                            if any(ev in data for ev in events):
                                on_change_callback()
                except Exception:
                    pass

        self._event_thread = threading.Thread(target=_worker, daemon=True)
        self._event_thread.start()
