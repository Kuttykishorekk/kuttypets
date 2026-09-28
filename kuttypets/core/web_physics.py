"""
OmniPet - Spider-Man Constrained Pendulum Web Physics Engine.
Computes tension, fixed-length rope kinematics, release arcs, and procedural silk strands.
"""

from __future__ import annotations
import math
import random
from typing import Dict, Any, List, Tuple

class WebPhysicsEngine:
    """Manages Spider-Man constrained pendulum dynamics and silk afterimages."""

    def __init__(self, gravity: float = 650.0):
        self.gravity = gravity
        self.web_active: bool = False
        self.web_anchor_x: float = 0.0
        self.web_anchor_y: float = 0.0
        self.web_length: float = 120.0
        self.web_opacity: float = 0.0
        self.web_duration: float = 0.0
        self.web_swings_left: int = 0
        self.web_tension: float = 0.0
        self.web_ghosts: List[Dict[str, Any]] = []

    def start_swing(
        self,
        pet_x: float,
        pet_y: float,
        win: Dict[str, Any],
        orbit_dir: int = 1,
        swings_count: int = 3,
    ) -> Tuple[float, float]:
        """Anchors web line to window header and computes initial swing release impulse."""
        self.web_active = True
        self.web_duration = 0.0
        self.web_swings_left = swings_count
        self.web_opacity = 1.0

        # Anchor web to window top rail header
        x1, x2 = float(win["x1"]), float(win["x2"])
        yt = float(win["y_top"])
        
        if orbit_dir > 0:
            self.web_anchor_x = min(x2 - 30.0, pet_x + random.uniform(60.0, 110.0))
        else:
            self.web_anchor_x = max(x1 + 30.0, pet_x - random.uniform(60.0, 110.0))
        self.web_anchor_y = yt

        dx = pet_x - self.web_anchor_x
        dy = pet_y - self.web_anchor_y
        self.web_length = max(50.0, math.hypot(dx, dy))

        # Initial tangential velocity impulse
        vx = orbit_dir * random.uniform(180.0, 260.0)
        vy = random.uniform(20.0, 60.0)
        return vx, vy

    def step_swing(
        self,
        dt: float,
        x: float,
        y: float,
        vx: float,
        vy: float,
        air_drag: float = 0.992,
    ) -> Tuple[float, float, float, float, float, bool]:
        """Steps fixed-length pendulum rope constraint with damping and returns (x, y, vx, vy, tilt, finished)."""
        self.web_duration += dt
        
        # Apply gravity and air drag
        vy += self.gravity * 0.95 * dt
        drag = math.pow(air_drag, dt * 60.0)
        vx *= drag
        vy *= drag

        x += vx * dt
        y += vy * dt

        ax, ay = self.web_anchor_x, self.web_anchor_y
        dx = x - ax
        dy = y - ay
        dist = math.hypot(dx, dy)
        rest = self.web_length

        if dist > 0.001:
            ux, uy = dx / dist, dy / dist
            if dist > rest * 1.01:
                x = ax + ux * rest
                y = ay + uy * rest
                v_rad = vx * ux + vy * uy
                if v_rad > 0.0:
                    vx -= ux * v_rad
                    vy -= uy * v_rad
            elif dist < rest * 0.90:
                pull = (rest - dist) * 22.0
                vx += ux * pull * dt
                vy += uy * pull * dt
            else:
                v_rad = vx * ux + vy * uy
                vx -= ux * v_rad * 0.9
                vy -= uy * v_rad * 0.9

        self.web_tension = max(0.0, min(1.5, (dist / rest) - 0.92) * 6.0)
        ang = math.atan2(dx, max(1.0, dy))
        tilt = max(-0.55, min(0.55, -ang * 0.28 + vx * 0.0007))

        # Update ghost trails
        if self.web_ghosts:
            for g in self.web_ghosts:
                g["a"] -= dt * 0.70
            self.web_ghosts = [g for g in self.web_ghosts if g["a"] > 0.04][:6]

        finished = (self.web_duration > 1.8 and vy < -20.0 and abs(ang) > 0.35) or (self.web_duration > 3.2)
        return x, y, vx, vy, tilt, finished

    def push_web_ghost(self, hx: float, hy: float) -> None:
        """Saves a fading ghost trail of the web strand for photorealistic afterimages."""
        self.web_ghosts.append({
            "x0": hx, "y0": hy,
            "x1": self.web_anchor_x, "y1": self.web_anchor_y,
            "a": 0.85,
        })
