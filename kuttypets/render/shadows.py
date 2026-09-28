"""
OmniPet - Directional Ambient Occlusion Contact Shadow Engine.
Renders contact shadows anchored to live window bezels, rails, and sills.
"""

from __future__ import annotations
import math
from typing import Dict, Any

class ShadowEngine:
    """Calculates ambient occlusion shadow parameters based on pet posture and contact surface."""

    @staticmethod
    def get_contact_shadow_params(
        state: str,
        side: str,
        x: float,
        y: float,
        step_bob: float,
        render_scale: float,
        grip_catch_x: float = 0.0,
        grip_catch_y: float = 0.0,
        is_shimeji: bool = True,
    ) -> Dict[str, Any]:
        rs = render_scale

        if state == "CLINGING" and side in ("RIGHT", "LEFT"):
            wall_dir = -1.0 if side == "RIGHT" else 1.0
            reach = 17.0 * rs if is_shimeji else 12.0 * rs
            return {
                "type": "vertical_wall",
                "x": x + wall_dir * reach,
                "y": y - step_bob,
                "scale_x": 0.18,
                "scale_y": 1.20,
                "radius": 20.0 * rs,
                "alpha": 0.14,
            }
        elif state in ("CLINGING", "WINDOW_TOP_HANG", "SITTING") and side == "TOP":
            return {
                "type": "horizontal_rail",
                "x": x,
                "y": y + 19.0 * rs,
                "scale_x": 1.25,
                "scale_y": 0.22,
                "radius": 26.0 * rs,
                "alpha": 0.22,
            }
        elif state == "CLINGING" and side == "BOTTOM":
            return {
                "type": "sill_shadow",
                "x": x,
                "y": y - step_bob + 60.0 * rs,
                "scale_x": 1.20,
                "scale_y": 0.24,
                "radius": 26.0 * rs,
                "alpha": 0.20,
            }
        elif state == "CORNER_ARC":
            return {
                "type": "corner_shadow",
                "x": grip_catch_x or x,
                "y": grip_catch_y or y,
                "scale_x": 1.0,
                "scale_y": 1.0,
                "radius": 8.5 * rs,
                "alpha": 0.24,
            }
        else:
            # Floor / default standing contact shadow
            return {
                "type": "floor_shadow",
                "x": x,
                "y": y - step_bob + 60.0 * rs,
                "scale_x": 1.15,
                "scale_y": 0.28,
                "radius": 28.0 * rs,
                "alpha": 0.18,
            }
