"""
OmniPet - Biomechanical Kinematics, Corner Arcs & Stride Gait Engine.
"""

from __future__ import annotations
import math
from typing import Dict, Any, Tuple, Optional

class KinematicsEngine:
    """Computes realistic curves, biomechanical squash/stretch, and gait cycles."""

    @staticmethod
    def edge_end_factor(pos: float, start: float, end: float, travel_dir: float, slow_dist: float = 72.0) -> float:
        """Calculates quintic polynomial deceleration factor when approaching edge ends."""
        if travel_dir > 0:
            remain = end - pos
        else:
            remain = pos - start
        if remain >= slow_dist:
            return 1.0
        if remain <= 6.0:
            return 0.0
        # Quintic smoothstep: 6t^5 - 15t^4 + 10t^3
        t = max(0.0, min(1.0, remain / slow_dist))
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    @staticmethod
    def compute_stride_gait(tick: float, speed: float, cadence: float = 14.0) -> Tuple[float, float, float]:
        """Calculates foot-plant stride phase, vertical bob, and body lean."""
        phase = (tick * cadence) % (2.0 * math.pi)
        stride_sin = math.sin(phase)
        # Weight plant occurs when foot contacts the surface
        plant = max(0.0, math.cos(phase))
        # Speed-dependent stride multiplier
        smul = 1.0 + 0.08 * stride_sin if abs(speed) > 5.0 else 1.0
        return phase, plant, smul

    @staticmethod
    def compute_corner_geometry(
        win: Dict[str, Any],
        from_side: str,
        to_side: str,
        render_scale: float,
        hypr_rounding: float = 24.0,
        hypr_border_size: float = 2.0,
        stand_bot_y: float = 0.0,
        x_on_left_wall: float = 0.0,
        x_on_right_wall: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Calculates precise physical corner trajectories around rounded window frames."""
        if not win:
            return None

        R = max(8.0, float(hypr_rounding))
        border_size = max(1.0, float(hypr_border_size))
        R_eff = R + border_size
        rs = max(0.2, float(render_scale))
        radius = R_eff + 18.0 * rs

        x1, x2 = float(win["x1"]), float(win["x2"])
        yt, yb = float(win["y_top"]), float(win["y_bot"])
        pair = (from_side, to_side)

        table = {
            ("RIGHT", "TOP"):    dict(cx=x2 - R_eff, cy=yt + R_eff, a0=0.0,            a1=-math.pi * 0.5),
            ("TOP", "RIGHT"):    dict(cx=x2 - R_eff, cy=yt + R_eff, a0=-math.pi * 0.5, a1=0.0),
            ("TOP", "LEFT"):     dict(cx=x1 + R_eff, cy=yt + R_eff, a0=-math.pi * 0.5, a1=-math.pi),
            ("LEFT", "TOP"):     dict(cx=x1 + R_eff, cy=yt + R_eff, a0=-math.pi,        a1=-math.pi * 0.5),
            ("LEFT", "BOTTOM"):  dict(cx=x1 + R_eff, cy=yb - R_eff, a0=math.pi,         a1=math.pi * 0.5),
            ("BOTTOM", "LEFT"):  dict(cx=x1 + R_eff, cy=yb - R_eff, a0=math.pi * 0.5,   a1=math.pi),
            ("BOTTOM", "RIGHT"): dict(cx=x2 - R_eff, cy=yb - R_eff, a0=math.pi * 0.5,   a1=0.0),
            ("RIGHT", "BOTTOM"): dict(cx=x2 - R_eff, cy=yb - R_eff, a0=0.0,            a1=math.pi * 0.5),
        }
        spec = table.get(pair)
        if not spec:
            return None
        
        spec = dict(spec)
        spec["radius"] = radius
        spec["R"] = R_eff
        spec["is_bottom"] = (from_side == "BOTTOM" or to_side == "BOTTOM")

        if spec["is_bottom"]:
            sill_x_left = x1 + 44.0 * rs
            sill_x_right = x2 - 44.0 * rs

            if pair == ("LEFT", "BOTTOM"):
                spec["start_x"] = x_on_left_wall
                spec["start_y"] = yb - R_eff - 6.0 * rs
                spec["dest_x"] = sill_x_left
                spec["dest_y"] = stand_bot_y
                spec["ctrl_x"] = x_on_left_wall + (sill_x_left - x_on_left_wall) * 0.25
                spec["ctrl_y"] = yb - 2.0 * rs
            elif pair == ("BOTTOM", "LEFT"):
                spec["start_x"] = sill_x_left
                spec["start_y"] = stand_bot_y
                spec["dest_x"] = x_on_left_wall
                spec["dest_y"] = yb - R_eff - 10.0 * rs
                spec["ctrl_x"] = x_on_left_wall + (sill_x_left - x_on_left_wall) * 0.25
                spec["ctrl_y"] = yb - 2.0 * rs
            elif pair == ("RIGHT", "BOTTOM"):
                spec["start_x"] = x_on_right_wall
                spec["start_y"] = yb - R_eff - 6.0 * rs
                spec["dest_x"] = sill_x_right
                spec["dest_y"] = stand_bot_y
                spec["ctrl_x"] = x_on_right_wall + (sill_x_right - x_on_right_wall) * 0.25
                spec["ctrl_y"] = yb - 2.0 * rs
            elif pair == ("BOTTOM", "RIGHT"):
                spec["start_x"] = sill_x_right
                spec["start_y"] = stand_bot_y
                spec["dest_x"] = x_on_right_wall
                spec["dest_y"] = yb - R_eff - 10.0 * rs
                spec["ctrl_x"] = x_on_right_wall + (sill_x_right - x_on_right_wall) * 0.25
                spec["ctrl_y"] = yb - 2.0 * rs

        return spec

    @staticmethod
    def evaluate_corner_step(
        u: float,
        dt: float,
        meta: Dict[str, Any],
        render_scale: float,
    ) -> Dict[str, Any]:
        """Steps dynamic Bezier / circular corner progression with muscle pull-up effort."""
        e = u * u * (3.0 - 2.0 * u)
        
        # Muscle squash and stretch during pull-up
        if 0.20 <= u <= 0.80:
            effort = math.sin((u - 0.20) / 0.60 * math.pi)
            target_sy = 1.0 - 0.065 * effort
            target_sx = 1.0 + 0.045 * effort
        else:
            target_sy = 1.0
            target_sx = 1.0

        if meta.get("is_bottom", False):
            omt = 1.0 - e
            bx = (omt * omt) * meta["start_x"] + (2.0 * omt * e) * meta["ctrl_x"] + (e * e) * meta["dest_x"]
            by = (omt * omt) * meta["start_y"] + (2.0 * omt * e) * meta["ctrl_y"] + (e * e) * meta["dest_y"]
            
            de = min(1.0, e + 0.02)
            omte = 1.0 - de
            nx = (omte * omte) * meta["start_x"] + (2.0 * omte * de) * meta["ctrl_x"] + (de * de) * meta["dest_x"]
            ny = (omte * omte) * meta["start_y"] + (2.0 * omte * de) * meta["ctrl_y"] + (de * de) * meta["dest_y"]
            lean = math.atan2(ny - by, abs(nx - bx) + 1e-4) * 0.35
            
            return {
                "x": bx, "y": by,
                "lean": lean,
                "scale_x": target_sx, "scale_y": target_sy,
                "catch_x": bx, "catch_y": by,
            }
        else:
            dang = meta["a1"] - meta["a0"]
            ang = meta["a0"] + dang * e
            r = meta["radius"]
            x = meta["cx"] + math.cos(ang) * r
            y = meta["cy"] + math.sin(ang) * r
            catch_x = meta["cx"] + math.cos(ang) * meta["R"]
            catch_y = meta["cy"] + math.sin(ang) * meta["R"]
            lean = dang * e * 0.65
            
            return {
                "x": x, "y": y,
                "lean": lean,
                "scale_x": target_sx, "scale_y": target_sy,
                "catch_x": catch_x, "catch_y": catch_y,
            }
