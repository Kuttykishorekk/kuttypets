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
        self.raw_facing = CHARACTER_TEMPLATES.get(char_id, {}).get("raw_facing", "RIGHT")

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

        # Corner Arcs & Cooldown
        self.corner_t: float = 0.0
        self.corner_meta: Optional[Dict[str, Any]] = None
        self.corner_phase: str = "plant"
        self.corner_cooldown: float = 0.0

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
        # Update raw facing from discovered templates
        template = CHARACTER_TEMPLATES.get(self.current_char, {})
        self.raw_facing = template.get("raw_facing", "RIGHT" if "climb1" in rigs else "LEFT")

    def get_current_rig(self, frame_key: str) -> Dict[str, float]:
        return self.sprite_rigs.get(frame_key, {
            "width": 64.0, "height": 110.0,
            "left_reach": -25.0, "right_reach": 25.0,
            "grip_left_reach": -22.0, "grip_right_reach": 22.0,
            "top_reach": -55.0, "bottom_reach": 55.0,
            "grip_top_reach": -48.0, "grip_bottom_reach": 55.0,
        })

    def upright_foot_reach(self) -> float:
        for key in ("walk1", "id1_1", "shime1", "shime5", "shime11", "climb1"):
            rig = self.sprite_rigs.get(key)
            if rig and "bottom_reach" in rig:
                return abs(float(rig["bottom_reach"])) * float(self.render_scale)
        return 63.0 * float(self.render_scale)

    def compute_stand_y(self, ground_edge: float) -> float:
        contact = self.upright_foot_reach()
        return float(ground_edge) - contact

    def compute_bottom_cling_y(self, border_bot: float, is_sitting: bool = False) -> float:
        rs = max(0.2, float(self.render_scale))
        if is_sitting:
            seat_reach = 63.0 * rs
            return float(border_bot) - seat_reach
        return float(border_bot) - self.upright_foot_reach()

    def get_climb_hand_reach(self) -> float:
        """Calculates exact forward reach from sprite center to hands in climbing frames."""
        for k in ("climb1", "shime12", "climb2", "shime13", "id1_1", "shime1"):
            rig = self.sprite_rigs.get(k)
            if rig:
                if self.raw_facing == "LEFT":
                    return abs(float(rig.get("left_reach", -20.0)))
                else:
                    return abs(float(rig.get("right_reach", 52.0)))
        return 48.0

    def get_sprite_half_width(self) -> float:
        """Dynamic horizontal half-width based on loaded character rigs and render scale."""
        for key in ("walk1", "id1_1", "shime1", "shime11", "climb1"):
            rig = self.sprite_rigs.get(key)
            if rig and "right_reach" in rig and "left_reach" in rig:
                return (abs(float(rig["right_reach"])) + abs(float(rig["left_reach"]))) * 0.5 * float(self.render_scale)
        return 32.0 * float(self.render_scale)

    def get_corner_clearance_margin(self) -> float:
        """Dynamic clearance margin away from corner vertices."""
        rs = max(0.2, float(self.render_scale))
        metrics = self.adapter.get_layout_metrics()
        rounding = float(metrics.get("rounding", 8.0))
        border = float(metrics.get("border_size", 1.0))
        hand = self.get_climb_hand_reach() * rs
        return max(24.0 * rs, rounding + border + hand * 0.7)

    def get_edge_trigger_margin(self) -> float:
        """Dynamic edge deceleration trigger margin based on character scale and layout metrics."""
        rs = max(0.2, float(self.render_scale))
        metrics = self.adapter.get_layout_metrics()
        rounding = float(metrics.get("rounding", 8.0))
        half_w = self.get_sprite_half_width()
        return max(20.0 * rs, half_w * 0.9 + rounding * 0.5)

    def compute_outward_cling_x(self, wall_x: float, side: str) -> float:
        rs = max(0.2, float(self.render_scale))
        hand_reach = self.get_climb_hand_reach() * rs
        grip_bite = max(0.5, 1.2 * rs)
        if side == "RIGHT":
            return float(wall_x) + hand_reach - grip_bite
        else:
            return float(wall_x) - hand_reach + grip_bite

    def start_drag(self, cursor_x: float, cursor_y: float) -> None:
        """Begins interactive dragging at cursor position."""
        self.is_dragging = True
        self.drag_offset_x = cursor_x - self.x
        self.drag_offset_y = cursor_y - self.y
        self.state = "DRAGGING"
        self.vx = 0.0
        self.vy = 0.0
        self.mouse_history = [(time.time(), cursor_x, cursor_y)]

    def update_drag(self, cursor_x: float, cursor_y: float) -> None:
        """Updates pet position while being dragged."""
        if not self.is_dragging:
            return
        self.x = cursor_x - self.drag_offset_x
        self.y = cursor_y - self.drag_offset_y
        now = time.time()
        self.mouse_history.append((now, cursor_x, cursor_y))
        if len(self.mouse_history) > 8:
            self.mouse_history.pop(0)

    def end_drag(self) -> None:
        """Ends drag and launches pet with throw momentum."""
        if not self.is_dragging:
            return
        self.is_dragging = False
        self.state = "FALLING"
        if len(self.mouse_history) >= 2:
            t0, x0, y0 = self.mouse_history[0]
            t1, x1, y1 = self.mouse_history[-1]
            dt = max(0.016, t1 - t0)
            self.vx = (x1 - x0) / dt
            self.vy = (y1 - y0) / dt
        self.mouse_history.clear()

    def tick(self, dt: Optional[float] = None) -> None:
        now = time.time()
        if dt is None:
            dt = min(0.05, max(0.001, now - self.last_time))
        self.last_time = now
        self.update_physics(dt)

    def update_physics(self, dt: float) -> None:
        self.state_timer += dt
        self.anim_tick += dt
        self.particles.update(dt)

        if self.no_cling_timer > 0:
            self.no_cling_timer = max(0.0, self.no_cling_timer - dt)
        if self.corner_cooldown > 0:
            self.corner_cooldown = max(0.0, self.corner_cooldown - dt)

        # Smooth 3D turning perspective interpolation
        self.facing_scale += (self.facing - self.facing_scale) * min(1.0, dt * 16.0)

        if self.is_dragging:
            self.step_bob_y = 0.0
            return

        windows = self.adapter.get_windows()
        screen = self.adapter.get_screen_geometry()
        metrics = self.adapter.get_layout_metrics()
        screen_h = screen["height"]

        # Keep cling_target_window in sync with live window movement / closing
        if self.cling_target_window:
            matched = False
            for w in windows:
                if w.address == self.cling_target_window.address:
                    self.cling_target_window = w
                    matched = True
                    break
            if not matched and self.state in ("CLINGING", "CORNER_ARC"):
                # Window was closed or moved off-screen: release pet cleanly into freefall
                self.state = "FALLING"
                self.cling_target_window = None
                self.corner_meta = None
                self.vx = 0.0
                self.vy = 40.0
                return

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
                from_side = self.corner_meta.get("from_side", "TOP")
                to_side = self.corner_meta.get("to_side", "TOP")
                w = self.cling_target_window
                self.state = "CLINGING"
                self.cling_side = to_side
                self.target_body_angle = 0.0
                self.body_angle = 0.0
                self.state_timer = 0.0
                self.corner_cooldown = 1.0  # Prevent immediate corner re-trigger

                clearance = self.get_corner_clearance_margin()
                if to_side == "BOTTOM":
                    self.cling_mode = "BOTTOM_CRAWL"
                    self.cling_orbit = 1 if from_side == "LEFT" else -1
                    if w:
                        self.x = w.x1 + clearance if from_side == "LEFT" else w.x2 - clearance
                elif to_side == "TOP":
                    self.cling_mode = "TOP_CRAWL"
                    self.cling_orbit = 1 if from_side == "LEFT" else -1
                    if w:
                        self.x = w.x1 + clearance if from_side == "LEFT" else w.x2 - clearance
                else:
                    # to_side is "LEFT" or "RIGHT"
                    if from_side == "TOP":
                        self.cling_mode = "WALL_SLIDE"  # Crawl DOWN away from top
                        if w:
                            self.y = w.y_top + clearance
                    else:
                        self.cling_mode = "CLIMB_UP"    # Crawl UP away from bottom
                        if w:
                            self.y = w.y_bot - clearance
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
        profile = PRESENCE_PROFILES.get(self.presence_mode, PRESENCE_PROFILES["calm"])
        edge_margin = self.get_edge_trigger_margin()
        slow_dist = max(32.0 * self.render_scale, edge_margin * 1.6)
        base_spd = profile.get("walk_speed", 52.0)
        crawl_spd = max(18.0, base_spd * max(0.4, float(self.render_scale)))

        if self.state == "CLINGING":
            if not self.cling_target_window:
                self.state = "FALLING"
                self.vy = 40.0
                return
            w = self.cling_target_window
            if self.cling_side == "BOTTOM":
                self.y = self.compute_bottom_cling_y(w.y_bot)
                travel = 1.0 if self.cling_orbit > 0 else -1.0
                self.facing = travel
                brake = KinematicsEngine.edge_end_factor(self.x, w.x1 + edge_margin, w.x2 - edge_margin, travel, slow_dist=slow_dist)
                spd = max(16.0, crawl_spd * brake) * travel
                self.vx = spd
                self.x += self.vx * dt

                if self.corner_cooldown <= 0:
                    if travel > 0 and (self.x >= w.x2 - edge_margin or brake < 0.15):
                        self.start_corner(w, "BOTTOM", "RIGHT")
                    elif travel < 0 and (self.x <= w.x1 + edge_margin or brake < 0.15):
                        self.start_corner(w, "BOTTOM", "LEFT")
            elif self.cling_side == "TOP":
                self.y = self.compute_stand_y(w.y_top)
                travel = 1.0 if self.cling_orbit > 0 else -1.0
                self.facing = travel
                brake = KinematicsEngine.edge_end_factor(self.x, w.x1 + edge_margin, w.x2 - edge_margin, travel, slow_dist=slow_dist)
                spd = max(16.0, crawl_spd * brake) * travel
                self.vx = spd
                self.x += self.vx * dt

                if self.corner_cooldown <= 0:
                    if travel > 0 and (self.x >= w.x2 - edge_margin or brake < 0.15):
                        self.start_corner(w, "TOP", "RIGHT")
                    elif travel < 0 and (self.x <= w.x1 + edge_margin or brake < 0.15):
                        self.start_corner(w, "TOP", "LEFT")
            elif self.cling_side in ("LEFT", "RIGHT"):
                wall_x = w.x2 if self.cling_side == "RIGHT" else w.x1
                self.x = self.compute_outward_cling_x(wall_x, self.cling_side)
                self.facing = 1.0 if self.cling_side == "LEFT" else -1.0

                travel_y = 1.0 if self.cling_mode == "WALL_SLIDE" else -1.0
                brake = KinematicsEngine.edge_end_factor(self.y, w.y_top + edge_margin, w.y_bot - edge_margin, travel_y, slow_dist=slow_dist)
                spd = max(14.0, (crawl_spd * 0.85) * brake) * travel_y
                self.vy = spd
                self.y += self.vy * dt

                if self.corner_cooldown <= 0:
                    if travel_y > 0 and (self.y >= w.y_bot - edge_margin or brake < 0.15):
                        self.start_corner(w, self.cling_side, "BOTTOM")
                    elif travel_y < 0 and (self.y <= w.y_top + edge_margin or brake < 0.15):
                        self.start_corner(w, self.cling_side, "TOP")

            # Break out of cling after 4 to 8 seconds of crawling for active variety
            if self.state_timer >= random.uniform(4.5, 8.0):
                self.state_timer = 0.0
                if self.cling_side == "TOP":
                    self.state = "SITTING"
                    self.vx = 0.0
                elif self.cling_side in ("LEFT", "RIGHT"):
                    can_swing = CHARACTER_TEMPLATES.get(self.current_char, {}).get("can_swing", False)
                    if can_swing and random.random() < 0.6:
                        self.vx, self.vy = self.web.start_swing(self.x, self.y, w.to_dict())
                        self.state = "SWINGING"
                    else:
                        self.state = "FALLING"
                        self.vy = -random.uniform(60.0, 120.0)
                        self.vx = -self.facing * random.uniform(50.0, 90.0)
                        self.no_cling_timer = 1.5
                else:
                    self.state = "FALLING"
                    self.vy = random.uniform(30.0, 70.0)
                    self.no_cling_timer = 1.5
            return

        # -------------------------------------------------------------
        # 5. IDLE / SITTING / WALKING / SPECIAL
        # -------------------------------------------------------------
        screen_w = screen.get("width", 1920.0)

        if self.state in ("IDLE", "SITTING"):
            self.vx = 0.0
            self.step_bob_y = 0.0
            if self.cling_target_window:
                if self.cling_side == "BOTTOM":
                    self.y = self.compute_bottom_cling_y(self.cling_target_window.y_bot, is_sitting=True)
                else:
                    self.y = self.compute_stand_y(self.cling_target_window.y_top)
            else:
                floor_y = self.compute_stand_y(screen_h - metrics.get("gap_bottom", 0.0))
                self.y = floor_y

            sit_min, sit_max = profile.get("idle_sit", (3.0, 7.0))
            if self.state_timer >= sit_min:
                self.state_timer = 0.0
                roll = random.random()

                # Check Spider-Man web swinging chance
                can_swing = CHARACTER_TEMPLATES.get(self.current_char, {}).get("can_swing", False)
                if can_swing and windows and roll < profile.get("leap_chance", 0.18):
                    w = random.choice(windows)
                    self.vx, self.vy = self.web.start_swing(self.x, self.y, w.to_dict())
                    self.state = "SWINGING"
                    return

                if roll < 0.72:
                    self.state = "WALKING"
                    self.facing = 1.0 if random.random() > 0.5 else -1.0
                    spd = max(24.0, profile.get("walk_speed", 52.0) * max(0.4, float(self.render_scale)))
                    self.vx = spd * self.facing
                elif roll < 0.90:
                    self.state = "SPECIAL"
                    self.vx = 0.0
                else:
                    # Hop into air
                    self.state = "FALLING"
                    self.vy = -random.uniform(160.0, 240.0)
                    self.vx = random.uniform(-40.0, 40.0)
                    return

        elif self.state == "SPECIAL":
            self.vx = 0.0
            self.step_bob_y = 0.0
            if self.cling_target_window:
                self.y = self.compute_stand_y(self.cling_target_window.y_top)
            else:
                self.y = self.compute_stand_y(screen_h - metrics.get("gap_bottom", 0.0))

            if self.state_timer >= 3.5:
                self.state = "WALKING"
                self.state_timer = 0.0
                self.facing = 1.0 if random.random() > 0.5 else -1.0
                spd = max(24.0, profile.get("walk_speed", 52.0) * max(0.4, float(self.render_scale)))
                self.vx = spd * self.facing

        elif self.state == "WALKING":
            self.x += self.vx * dt
            self.step_bob_y = math.sin(self.anim_tick * 12.0) * 1.6 * self.render_scale

            # Spawn subtle stride particles
            if random.random() < profile.get("slide_particle", 0.08):
                ptype = CHARACTER_TEMPLATES.get(self.current_char, {}).get("particle", "sparkle")
                self.particles.emit(1, self.x - self.facing * 12.0 * self.render_scale, self.y + self.upright_foot_reach() * 0.8, ptype)

            # Walking on top of a window
            if self.cling_target_window:
                w = self.cling_target_window
                self.y = self.compute_stand_y(w.y_top)

                if self.vx > 0 and self.x >= w.x2 - edge_margin:
                    if random.random() < 0.65 and self.corner_cooldown <= 0:
                        self.start_corner(w, "TOP", "RIGHT")
                        return
                    else:
                        self.facing = -1.0
                        self.vx = -abs(self.vx)
                elif self.vx < 0 and self.x <= w.x1 + edge_margin:
                    if random.random() < 0.65 and self.corner_cooldown <= 0:
                        self.start_corner(w, "TOP", "LEFT")
                        return
                    else:
                        self.facing = 1.0
                        self.vx = abs(self.vx)
            else:
                # Walking on desktop floor
                floor_y = self.compute_stand_y(screen_h - metrics.get("gap_bottom", 0.0))
                self.y = floor_y

                if self.vx > 0 and self.x >= screen_w - edge_margin:
                    self.facing = -1.0
                    self.vx = -abs(self.vx)
                elif self.vx < 0 and self.x <= edge_margin:
                    self.facing = 1.0
                    self.vx = abs(self.vx)

            # Sit down after walk interval
            if self.state_timer >= random.uniform(4.0, 9.0):
                self.state = "SITTING"
                self.state_timer = 0.0
                self.vx = 0.0

    def start_corner(self, win: WindowInfo, from_side: str, to_side: str) -> None:
        self.cling_target_window = win
        metrics = self.adapter.get_layout_metrics()
        x_left = self.compute_outward_cling_x(win.x1, "LEFT")
        x_right = self.compute_outward_cling_x(win.x2, "RIGHT")
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
            self.corner_cooldown = 1.0
            return
        
        meta["from_side"] = from_side
        meta["to_side"] = to_side
        self.corner_meta = meta
        self.corner_t = 0.0
        self.state = "CORNER_ARC"
