"""
OmniPet - Abstract Window and Display Adapter Interface.
Defines contracts for querying on-screen window geometry, active apps, and screen bounds.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable

class WindowInfo:
    """Standardized cross-platform window descriptor."""
    def __init__(
        self,
        address: str,
        x1: float,
        x2: float,
        y_top: float,
        y_bot: float,
        title: str = "",
        app_class: str = "",
        is_active: bool = False,
        is_floating: bool = False,
    ):
        self.address = address
        self.x1 = x1
        self.x2 = x2
        self.y_top = y_top
        self.y_bot = y_bot
        self.title = title
        self.app_class = app_class
        self.is_active = is_active
        self.is_floating = is_floating

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "x1": self.x1,
            "x2": self.x2,
            "y_top": self.y_top,
            "y_bot": self.y_bot,
            "title": self.title,
            "class": self.app_class,
            "is_active": self.is_active,
            "is_floating": self.is_floating,
        }

class BaseWindowAdapter(ABC):
    """Abstract interface that every OS must implement."""

    @abstractmethod
    def get_windows(self) -> List[WindowInfo]:
        """Returns a list of all visible on-screen windows in logical display coordinates."""
        pass

    @abstractmethod
    def get_active_window(self) -> Optional[WindowInfo]:
        """Returns the currently focused / active foreground window."""
        pass

    @abstractmethod
    def get_screen_geometry(self) -> Dict[str, float]:
        """Returns the primary screen geometry: {'width': float, 'height': float, 'scale': float}."""
        pass

    @abstractmethod
    def get_layout_metrics(self) -> Dict[str, float]:
        """Returns OS/WM decoration metrics: {'rounding': float, 'border_size': float, 'gap_top': float, 'gap_bottom': float}."""
        pass

    def start_event_listener(self, on_change_callback: Callable[[], None]) -> None:
        """Optional subscription for real-time window movement / workspace change notifications."""
        pass
