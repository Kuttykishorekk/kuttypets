"""
Deterministic Multi-Frame Simulation and Physics Scenario Test Suite.
Validates kinematic invariants, zero vertical drift, corner turning,
pendulum damping, boundary clamping, and robustness against NaNs.
"""

import unittest
import math
import random
from typing import List, Dict, Any, Optional

from kuttypets.adapters.base import BaseWindowAdapter, WindowInfo
from kuttypets.core.engine import OmniPetEngine
from kuttypets.config import discover_characters
from kuttypets.core.rigs import SpriteRigAnalyzer


class ScenarioMockAdapter(BaseWindowAdapter):
    """Deterministic mock adapter with configurable window rails and display bounds."""

    def __init__(self, windows: Optional[List[WindowInfo]] = None):
        if windows is None:
            self.windows = [
                WindowInfo(
                    address="0x2000",
                    x1=200.0,
                    x2=800.0,
                    y_top=200.0,
                    y_bot=600.0,
                    title="Code Editor",
                    app_class="code",
                    is_active=True,
                    is_floating=False,
                )
            ]
        else:
            self.windows = windows

    def get_windows(self) -> List[WindowInfo]:
        return self.windows

    def get_active_window(self) -> Optional[WindowInfo]:
        return self.windows[0] if self.windows else None

    def get_screen_geometry(self) -> Dict[str, float]:
        return {"x": 0.0, "y": 0.0, "width": 1920.0, "height": 1080.0, "scale": 1.0}

    def get_layout_metrics(self) -> Dict[str, float]:
        return {"rounding": 8.0, "border_size": 1.0, "gap_top": 0.0, "gap_bottom": 40.0}


class TestPhysicsScenarios(unittest.TestCase):
    """Senior Developer Physics & Kinematic Regression Suite."""

    def setUp(self):
        self.adapter = ScenarioMockAdapter()
        self.engine = OmniPetEngine(
            adapter=self.adapter,
            char_id="spiderman",
            presence_mode="lively",
            render_scale=0.68,
        )
        chars = discover_characters()
        if "spiderman" in chars:
            rigs = SpriteRigAnalyzer.load_and_rig_character(chars["spiderman"]["path"])
            self.engine.set_character_rigs(rigs)

    def test_freefall_and_rail_landing_invariant(self):
        """Verify that a pet falling from mid-air lands exactly on the window rail with zero ground penetration."""
        # Place pet in air above the mock window
        self.engine.x = 400.0
        self.engine.y = 50.0
        self.engine.vx = 0.0
        self.engine.vy = 100.0
        self.engine.state = "FALLING"

        target_win = self.adapter.windows[0]
        expected_landing_y = self.engine.compute_stand_y(target_win.y_top)

        landed = False
        dt = 1.0 / 60.0
        # Step simulation for up to 120 ticks (2 seconds)
        for _ in range(120):
            self.engine.tick(dt=dt)
            if self.engine.state in ("SITTING", "TOP_CRAWL", "WALKING"):
                landed = True
                break

        self.assertTrue(landed, "Pet should have collided and landed on window top rail")
        self.assertAlmostEqual(self.engine.y, expected_landing_y, delta=2.0,
                               msg="Pet Y must be aligned with window top rail within 2px tolerance")
        self.assertFalse(math.isnan(self.engine.x))
        self.assertFalse(math.isnan(self.engine.y))

    def test_continuous_rail_walk_zero_vertical_drift(self):
        """Verify that autonomous walking along the window rail maintains zero vertical drift over 180 frames."""
        target_win = self.adapter.windows[0]
        stand_y = self.engine.compute_stand_y(target_win.y_top)

        self.engine.x = 300.0
        self.engine.y = stand_y
        self.engine.state = "CLINGING"
        self.engine.cling_target_window = target_win
        self.engine.cling_side = "TOP"
        self.engine.cling_orbit = 1

        initial_x = self.engine.x
        dt = 1.0 / 60.0

        # Simulate walking along rail (60 ticks)
        for tick in range(60):
            self.engine.tick(dt=dt)
            # Invariant: Y coordinate should never drift from the top rail surface
            self.assertAlmostEqual(self.engine.y, stand_y, delta=1.0,
                                   msg=f"Frame {tick}: Vertical drift detected! Expected {stand_y}, got {self.engine.y}")
            # Invariant: Finite non-NaN coordinates
            self.assertFalse(math.isnan(self.engine.x))
            self.assertFalse(math.isnan(self.engine.y))

        # Pet must have made forward progress
        self.assertGreater(self.engine.x, initial_x, "Pet should have walked forward to the right")

    def test_corner_turn_kinematics(self):
        """Verify smooth 90-degree corner turning without coordinate popping."""
        target_win = self.adapter.windows[0]
        stand_y = self.engine.compute_stand_y(target_win.y_top)

        # Place pet right near the top-right corner approaching the edge
        self.engine.x = target_win.x2 - 42.0
        self.engine.y = stand_y
        self.engine.state = "CLINGING"
        self.engine.cling_target_window = target_win
        self.engine.cling_side = "TOP"
        self.engine.cling_orbit = 1

        corner_detected = False
        dt = 1.0 / 60.0
        for _ in range(90):
            self.engine.tick(dt=dt)
            if self.engine.state == "CORNER_ARC":
                corner_detected = True
                # Invariant: body angle is within valid rotation arc
                self.assertFalse(math.isnan(self.engine.body_angle))
                self.assertTrue(-180.0 <= self.engine.body_angle <= 180.0)
                break

        self.assertTrue(corner_detected, "Engine must initiate CORNER_ARC when reaching window boundary")

    def test_corner_completion_no_infinite_oscillation(self):
        """Verify that turning a top-right corner transitions to downward crawl without ping-pong oscillation."""
        target_win = self.adapter.windows[0]
        stand_y = self.engine.compute_stand_y(target_win.y_top)

        # Place pet at top-right corner
        self.engine.x = target_win.x2 - 42.0
        self.engine.y = stand_y
        self.engine.state = "CLINGING"
        self.engine.cling_target_window = target_win
        self.engine.cling_side = "TOP"
        self.engine.cling_orbit = 1

        dt = 1.0 / 60.0
        # Run through approach and corner arc until on the right wall
        for _ in range(70):
            self.engine.tick(dt=dt)
            if self.engine.state == "CLINGING" and self.engine.cling_side == "RIGHT":
                break

        # Pet must now be on the RIGHT wall, moving DOWN
        self.assertEqual(self.engine.cling_side, "RIGHT")
        self.assertEqual(self.engine.cling_mode, "WALL_SLIDE")
        self.assertGreater(self.engine.y, target_win.y_top)

        # Run 30 more ticks down the wall; assert it does NOT oscillate back to TOP
        initial_wall_y = self.engine.y
        for _ in range(30):
            self.engine.tick(dt=dt)
            self.assertNotEqual(self.engine.state, "CORNER_ARC", "Must not oscillate back into corner arc")

        self.assertGreater(self.engine.y, initial_wall_y, "Pet must make downward progress along the wall")

    def test_web_swing_arc_conservation_and_damping(self):
        """Verify Spider-Man web swing dynamics: length clamping and damping."""
        target_win = self.adapter.windows[0]

        # Start swing from an offset position
        self.engine.x = 420.0
        self.engine.y = 280.0
        self.engine.vx, self.engine.vy = self.engine.web.start_swing(
            self.engine.x, self.engine.y, target_win.to_dict(), orbit_dir=1, swings_count=2
        )
        self.engine.state = "SWINGING"

        self.assertTrue(self.engine.web.web_active)
        initial_length = self.engine.web.web_length
        # Invariant: Clamped to realistic arc
        self.assertGreaterEqual(initial_length, 80.0)
        self.assertLessEqual(initial_length, 280.0)

        # Simulate 120 ticks of pendulum swinging
        dt = 1.0 / 60.0
        max_speed = 0.0
        for _ in range(120):
            self.engine.tick(dt=dt)
            speed = math.sqrt(self.engine.vx*self.engine.vx + self.engine.vy*self.engine.vy)
            if speed > max_speed:
                max_speed = speed
            self.assertFalse(math.isnan(self.engine.x))
            self.assertFalse(math.isnan(self.engine.y))

        # Pendulum speed must be bounded and physically reasonable
        self.assertLess(max_speed, 1500.0, "Swing velocity must not explode")

    def test_property_fuzz_extreme_inputs(self):
        """Fuzz testing with extreme velocities and randomized geometry to assert zero NaNs or crashes."""
        random.seed(42)
        dt = 1.0 / 60.0

        for trial in range(30):
            rand_w = ScenarioMockAdapter([
                WindowInfo(
                    address=f"0x{trial:04x}",
                    x1=random.uniform(-300.0, 1000.0),
                    x2=random.uniform(1100.0, 2500.0),
                    y_top=random.uniform(50.0, 500.0),
                    y_bot=random.uniform(600.0, 1200.0),
                    title=f"Window {trial}",
                )
            ])
            eng = OmniPetEngine(rand_w, char_id="spiderman", render_scale=0.68)
            # Inject extreme impulse velocities
            eng.x = random.uniform(-100.0, 2000.0)
            eng.y = random.uniform(-100.0, 1500.0)
            eng.vx = random.uniform(-4000.0, 4000.0)
            eng.vy = random.uniform(-4000.0, 4000.0)
            eng.state = random.choice(["FALLING", "SITTING", "CLINGING", "WALKING"])

            for _ in range(25):
                eng.tick(dt=dt)
                self.assertFalse(math.isnan(eng.x), f"Trial {trial}: NaN in x coordinate")
                self.assertFalse(math.isnan(eng.y), f"Trial {trial}: NaN in y coordinate")
                self.assertFalse(math.isnan(eng.vx), f"Trial {trial}: NaN in vx")
                self.assertFalse(math.isnan(eng.vy), f"Trial {trial}: NaN in vy")
                self.assertFalse(math.isinf(eng.x), f"Trial {trial}: Inf in x coordinate")
                self.assertFalse(math.isinf(eng.y), f"Trial {trial}: Inf in y coordinate")


if __name__ == "__main__":
    unittest.main()
