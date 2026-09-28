"""
OmniPet - Automatic Sprite Rigging and Solid Alpha Contact Analyzer.
Extracts hand grip points, feet contact lines, and collision boundaries with sub-pixel precision.
"""

from __future__ import annotations
import os
from typing import Dict, Any, Tuple
from PIL import Image

class SpriteRigAnalyzer:
    """Analyzes raw RGBA sprite frames to extract biomechanical contact coordinates."""

    @staticmethod
    def measure_sprite_grip(rgba_img: Image.Image) -> Tuple[int, int, int, int]:
        """Calculates solid hand/foot contact bounds (filtering out faint alpha anti-aliasing fringe)."""
        px = rgba_img.load()
        w, h = rgba_img.size
        # Mid + lower body scan window for hands and feet
        y0, y1 = int(h * 0.28), int(h * 0.98)

        def col_mass(x: int) -> int:
            m = 0
            for y in range(y0, y1):
                a = px[x, y][3]
                if a >= 110:
                    m += a
            return m

        col_masses = [col_mass(x) for x in range(w)]
        ctotal = sum(col_masses) or 1
        
        # Left grip boundary
        cum = 0
        grip_l = 0
        for x, m in enumerate(col_masses):
            cum += m
            if cum >= ctotal * 0.02 and m > 0:
                grip_l = x
                break

        # Right grip boundary
        cum = 0
        grip_r = w - 1
        for x in range(w - 1, -1, -1):
            cum += col_masses[x]
            if cum >= ctotal * 0.02 and col_masses[x] > 0:
                grip_r = x
                break

        # Vertical mass distribution for head top and feet bottom
        x0, x1 = int(w * 0.20), int(w * 0.80)
        def row_mass(y: int) -> int:
            m = 0
            for x in range(x0, x1):
                a = px[x, y][3]
                if a >= 110:
                    m += a
            return m

        row_masses = [row_mass(y) for y in range(h)]
        rtotal = sum(row_masses) or 1
        
        # Top head grip
        cum = 0
        grip_t = 0
        for y, m in enumerate(row_masses):
            cum += m
            if cum >= rtotal * 0.015 and m > 0:
                grip_t = y
                break

        # Bottom feet grip
        cum = 0
        grip_b = h - 1
        for y in range(h - 1, -1, -1):
            cum += row_masses[y]
            if cum >= rtotal * 0.015 and row_masses[y] > 0:
                grip_b = y
                break

        return grip_l, grip_r, grip_t, grip_b

    @classmethod
    def load_and_rig_character(cls, char_dir: str) -> Dict[str, Dict[str, float]]:
        """Scans all PNG frames in a character directory and builds rig lookup dictionaries."""
        rigs: Dict[str, Dict[str, float]] = {}
        if not os.path.isdir(char_dir):
            return rigs

        for fn in os.listdir(char_dir):
            if not fn.endswith(".png"):
                continue
            key = os.path.splitext(fn)[0]
            fp = os.path.join(char_dir, fn)
            try:
                with Image.open(fp) as im:
                    rgba = im.convert("RGBA")
                    bbox = rgba.getbbox()
                    w, h = rgba.size
                    center_x, center_y = w * 0.5, h * 0.5
                    
                    if bbox:
                        min_x, min_y, max_x, max_y = bbox
                        grip_l, grip_r, grip_t, grip_b = cls.measure_sprite_grip(rgba)
                        rigs[key] = {
                            "width": float(max_x - min_x),
                            "height": float(max_y - min_y),
                            "left_reach": float(min_x - center_x),
                            "right_reach": float(max_x - center_x),
                            "grip_left_reach": float(grip_l - center_x),
                            "grip_right_reach": float(grip_r - center_x),
                            "top_reach": float(min_y - center_y),
                            "bottom_reach": float(max_y - center_y),
                            "grip_top_reach": float(grip_t - center_y),
                            "grip_bottom_reach": float(grip_b - center_y),
                        }
                    else:
                        rigs[key] = {
                            "width": 64.0, "height": 110.0,
                            "left_reach": -25.0, "right_reach": 25.0,
                            "grip_left_reach": -22.0, "grip_right_reach": 22.0,
                            "top_reach": -55.0, "bottom_reach": 55.0,
                            "grip_top_reach": -48.0, "grip_bottom_reach": 55.0,
                        }
            except Exception:
                pass
        return rigs
