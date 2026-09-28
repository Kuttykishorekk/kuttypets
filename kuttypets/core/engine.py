"""
OmniPet - Cross-Platform Game Loop, State Machine & Companion Physics Core.
"""

from __future__ import annotations
import time
import math
import random
from typing import Dict, Any, List, Optional, Tuple

from ..config import PRESENCE_PROFILES, CHARACTER_TEMPLATES
from .rigs import SpriteRigAnalyzer
from .kinematics import KinematicsEngine
from .web_physics import WebPhysicsEngine
from ..render.particles import ParticlePool
from ..adapters.base import BaseWindowAdapter, WindowInfo

class OmniPetEngine:
    """Platform-independent physics, gait, and state coordinator."""

    def __init__(self, adapter: BaseWindowAdapter, char_id: str = "spiderman", presence_mode: str = "calm", render_scale: float = 0.68):
        self.adapter = adapter
        self.current_char = char_id
        self.presence_mode = presence_mode
        self.render_scale = render_scale

        # Position and Kinematic Vectors
        self.x: float = 400.0
        self.y: float = 300.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.facing: float = 1.0
        self.facing_scale: float = 1.0
        self.target_body_angle: float = 0.0
        self.body_angle: float = 0.0
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.step_bob_y: float = 0.0
        self.draw_alpha: float = 1.0

        # State machine
        self.state: str = "SITTING"
        self.state_timer: float = 0.0
        self.anim_tick: float = 0.0
        self.last_time: float = time.time()
        self.gravity: float = 680.0
        self.air_drag: float = 0.992

        # Clinging & Windows
        self.cling_target_window: Optional[WindowInfo] = None
        self.cling_side: str = "TOP"
        self.cling_mode: str = "TOP_CRAWL"
        self.cling_mode_timer: float = 0.0
        self.cling_orbit: int = 1
        self.cling_duration: float = 8.0
        self.move_speed: float = 0.0
        self.gait_phase: float = 0.0
        self.no_cling_timer: float = 0.0

        # Corner Arcs
        self.corner_t: float = 0.0
        self.corner_meta: Optional[Dict[str, Any]] = None
        self.corner_phase: str = "plant"

        # Web Swinging (Spider-Man)
        self.web = WebPhysicsEngine(self.gravity)

        # Particle System
        self.particles = ParticlePool(capacity=32)

        # Rig caches
        self.sprite_rigs: Dict[str, Dict[str, float]] = {}

        # Dragging
        self.is_dragging: bool = False
        self.drag_offset_x: float = 0.0
        self.drag_offset_y: float = 0.0
        self.mouse_history: List[Tuple[float, float, float]] = []

    def set_character_rigs(self, rigs: Dict[str, Dict[str, float]]) -> None:
        self.sprite_rigs = rigs

    def get_current_rig(self, frame_key: str) -> Dict[str, float]:
        return self.sprite_rigs.get(frame_key, {
            "width": 64.0, "height": 110.0,
            "left_reach": -25.0, "right_reach": 25.0,
            "grip_left_reach": -22.0, "grip_right_reach": 22.0,
            "top_reach": -55.0, "bottom_reach": 55.0,
            "grip_top_reach": -48.0, "grip_bottom_reach": 55.0,
        })

    def upright_foot_reach(self) -> float:
        for key in ("shime1", "id1_1", "walk1", "shime5", "shime11", "climb1"):
            rig = self.sprite_rigs.get(key)
            if rig and "bottom_reach" in rig:
                return abs(float(rig["bottom_reach"])) * float(self.render_scale)
        return 63.0 * float(self.render_scale)

    def compute_stand_y(self, ground_edge: float) -> float:
        contact = self.upright_foot_reach()
        rs = max(0.2, float(self.render_scale))
        dig = max(1.0, 1.8 * rs)
        return float(ground_edge) - contact + dig

    def compute_bottom_cling_y(self, border_bot: float, is_sitting: bool = False) -> float:
        rs = max(0.2, float(self.render_scale))
        if is_sitting:
            seat_reach = 62.0 * rs
            return float(border_bot) - seat_reach
        return float(border_bot) - self.upright_foot_reach()

    def compute_outward_cling_x(self, wall_x: float, side: str, bounds: Dict[str, float]) -> float:
        rs = max(0.2, float(self.render_scale))
        grip_bite = max(1.2, 2.0 * rs)
        if side == "RIGHT":
            contact = float(bounds.get("grip_left_reach", -22.0 * rs))
            return float(wall_x) - contact - grip_bite
        else:
            contact = float(bounds.get("grip_right_reach", 22.0 * rs))
            return float(wall_x) - contact + grip_bite

    def tick(self) -> None:
        now = time.time()
        dt = min(0.05, max(0.001, now - self.last_time))
        self.last_time = now
        self.update_physics(dt)

    def update_physics(self, dt: float) -> None:
        self.state_timer += dt
        self.anim_tick += dt
        self.particles.update(dt)

        if self.no_cling_timer > 0:
            self.no_cling_timer = max(0.0, self.no_cling_timer - dt)

        # Smooth 3D turning perspective interpolation
        self.facing_scale += (self.facing - self.facing_scale) * min(1.0, dt * 16.0)

        if self.is_dragging:
            self.step_bob_y = 0.0
            return

        windows = self.adapter.get_windows()
        screen = self.adapter.get_screen_geometry()
        metrics = self.adapter.get_layout_metrics()
        screen_h = screen["height"]

        # -------------------------------------------------------------
        # 1. CORNER ARC
        # -------------------------------------------------------------
        if self.state == "CORNER_ARC":
            if not self.corner_meta:
                self.state = "SITTING"
                return
            dur = 0.46
            self.corner_t += dt / dur
            u = max(0.0, min(1.0, self.corner_t))
            res = KinematicsEngine.evaluate_corner_step(u, dt, self.corner_meta, self.render_scale)
            self.x = res["x"]
            self.y = res["y"]
            self.target_body_angle = res["lean"]
            self.body_angle += (self.target_body_angle - self.body_angle) * min(1.0, dt * 18.0)
            self.scale_x = res["scale_x"]
            self.scale_y = res["scale_y"]

            if u < 0.25:
                self.corner_phase = "plant"
            elif u < 0.60:
                self.corner_phase = "reach"
            elif u < 0.85:
                self.corner_phase = "pull"
            else:
                self.corner_phase = "settle"

            if u >= 1.0:
                self.state = "CLINGING"
                self.cling_side = self.corner_meta.get("to_side", "TOP")
                self.target_body_angle = 0.0
                self.body_angle = 0.0
                if self.cling_side == "BOTTOM":
                    self.cling_mode = "BOTTOM_CRAWL"
                elif self.cling_side == "TOP":
                    self.cling_mode = "TOP_CRAWL"
                else:
                    self.cling_mode = "CLIMB_UP"
            return

        # -------------------------------------------------------------
        # 2. SWINGING (Spider-Man)
        # -------------------------------------------------------------
        if self.state == "SWINGING":
            self.x, self.y, self.vx, self.vy, tilt, finished = self.web.step_swing(
                dt, self.x, self.y, self.vx, self.vy, self.air_drag
            )
            self.target_body_angle = tilt
            self.facing = 1.0 if self.vx >= 0 else -1.0
            if finished:
                self.state = "FALLING"
            return

        # -------------------------------------------------------------
        # 3. FALLING
        # -------------------------------------------------------------
        if self.state == "FALLING":
            self.step_bob_y = 0.0
            self.vy += self.gravity * dt
            self.vx *= math.pow(self.air_drag, dt * 60.0)
            prev_y = self.y
            self.x += self.vx * dt
            self.y += self.vy * dt

            # Catch window top
            for w in windows:
                if w.x1 - 15 <= self.x <= w.x2 + 15:
                    top_stand = self.compute_stand_y(w.y_top)
                    if prev_y <= top_stand + 20 and self.y >= top_stand - 12 and self.vy >= 0:
                        self.y = top_stand
                        self.state = "SITTING"
                        self.cling_target_window = w
                        self.vx = 0.0
                        self.vy = 0.0
                        return
                    bot_stand = self.compute_bottom_cling_y(w.y_bot)
                    if prev_y <= bot_stand + 22 and self.y >= bot_stand - 14 and self.vy >= 0:
                        self.y = bot_stand
                        self.state = "SITTING"
                        self.cling_target_window = w
                        self.cling_side = "BOTTOM"
                        self.vx = 0.0
                        self.vy = 0.0
                        return

            # Desktop floor landing
            floor_y = self.compute_stand_y(screen_h - metrics.get("gap_bottom", 0.0))
            if self.y >= floor_y and self.vy >= 0:
                self.y = floor_y
                self.state = "SITTING"
                self.cling_target_window = None
                self.vx = 0.0
                self.vy = 0.0
            return

        # -------------------------------------------------------------
        # 4. CLINGING (Perimeter Crawl / Wall Climb)
        # -------------------------------------------------------------
        if self.state == "CLINGING" and self.cling_target_window:
            w = self.cling_target_window
            if self.cling_side == "BOTTOM":
                self.y = self.compute_bottom_cling_y(w.y_bot)
                travel = 1.0 if self.cling_orbit > 0 else -1.0
                self.facing = travel
                brake = KinematicsEngine.edge_end_factor(self.x, w.x1 + 44.0, w.x2 - 44.0, travel)
                spd = 54.0 * brake * travel
                self.vx = spd
                self.x += self.vx * dt

                if travel > 0 and self.x >= w.x2 - 40.0 and brake < 0.45:
                    self.start_corner(w, "BOTTOM", "RIGHT")
                elif travel < 0 and self.x <= w.x1 + 40.0 and brake < 0.45:
                    self.start_corner(w, "BOTTOM", "LEFT")
            elif self.cling_side == "TOP":
                self.y = self.compute_stand_y(w.y_top)
                travel = 1.0 if self.cling_orbit > 0 else -1.0
                self.facing = travel
                brake = KinematicsEngine.edge_end_factor(self.x, w.x1 + 40.0, w.x2 - 40.0, travel)
                spd = 58.0 * brake * travel
                self.vx = spd
                self.x += self.vx * dt

                if travel > 0 and self.x >= w.x2 - 36.0 and brake < 0.45:
                    self.start_corner(w, "TOP", "RIGHT")
                elif travel < 0 and self.x <= w.x1 + 36.0 and brake < 0.45:
                    self.start_corner(w, "TOP", "LEFT")
            elif self.cling_side in ("LEFT", "RIGHT"):
                bounds = self.get_current_rig("climb1")
                wall_x = w.x2 if self.cling_side == "RIGHT" else w.x1
                self.x = self.compute_outward_cling_x(wall_x, self.cling_side, bounds)
                travel_y = 1.0 if self.cling_mode == "WALL_SLIDE" else -1.0
                brake = KinematicsEngine.edge_end_factor(self.y, w.y_top + 36.0, w.y_bot - 36.0, travel_y)
                spd = 46.0 * brake * travel_y
                self.vy = spd
                self.y += self.vy * dt

                if travel_y > 0 and self.y >= w.y_bot - 36.0 and brake < 0.45:
                    self.start_corner(w, self.cling_side, "BOTTOM")
                elif travel_y < 0 and self.y <= w.y_top + 36.0 and brake < 0.45:
                    self.start_corner(w, self.cling_side, "TOP")
            return

        # -------------------------------------------------------------
        # 5. IDLE / SITTING / WALKING
        # -------------------------------------------------------------
        if self.state in ("IDLE", "SITTING", "WALKING", "DANCE", "SPECIAL"):
            if self.cling_target_window:
                if self.cling_side == "BOTTOM":
                    self.y = self.compute_bottom_cling_y(self.cling_target_window.y_bot, is_sitting=(self.state != "WALKING"))
                else:
                    self.y = self.compute_stand_y(self.cling_target_window.y_top)
            else:
                floor_y = self.compute_stand_y(screen_h - metrics.get("gap_bottom", 0.0))
                self.y = floor_y

    def start_corner(self, win: WindowInfo, from_side: str, to_side: str) -> None:
        metrics = self.adapter.get_layout_metrics()
        bounds = self.get_current_rig("climb1")
        x_left = self.compute_outward_cling_x(win.x1, "LEFT", bounds)
        x_right = self.compute_outward_cling_x(win.x2, "RIGHT", bounds)
        stand_bot_y = self.compute_bottom_cling_y(win.y_bot)

        meta = KinematicsEngine.compute_corner_geometry(
            win.to_dict(), from_side, to_side, self.render_scale,
            hypr_rounding=metrics.get("rounding", 24.0),
            hypr_border_size=metrics.get("border_size", 2.0),
            stand_bot_y=stand_bot_y,
            x_on_left_wall=x_left,
            x_on_right_wall=x_right,
        )
        if not meta:
            self.state = "CLINGING"
            self.cling_side = to_side
            return
        
        meta["from_side"] = from_side
        meta["to_side"] = to_side
        self.corner_meta = meta
        self.corner_t = 0.0
        self.state = "CORNER_ARC"
