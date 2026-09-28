"""
Tests for Spider-Man web physics and pendulum kinematics.
"""

import unittest
from kuttypets.core.web_physics import WebPhysicsEngine

class TestWebPhysicsEngine(unittest.TestCase):
    def setUp(self):
        self.web = WebPhysicsEngine(gravity=650.0)

    def test_start_swing(self):
        fake_win = {
            "x1": 100.0,
            "x2": 800.0,
            "y_top": 150.0,
            "y_bot": 650.0,
        }
        vx, vy = self.web.start_swing(pet_x=300.0, pet_y=400.0, win=fake_win, orbit_dir=1, swings_count=3)
        self.assertTrue(self.web.web_active)
        self.assertGreater(self.web.web_length, 0.0)
        self.assertEqual(self.web.web_swings_left, 3)
        self.assertIsInstance(vx, float)
        self.assertIsInstance(vy, float)

    def test_step_swing(self):
        fake_win = {
            "x1": 100.0,
            "x2": 800.0,
            "y_top": 150.0,
            "y_bot": 650.0,
        }
        vx, vy = self.web.start_swing(pet_x=300.0, pet_y=400.0, win=fake_win, orbit_dir=1)
        x, y = 300.0, 400.0
        
        # Step several frames of physics
        for _ in range(10):
            x, y, vx, vy, tilt, finished = self.web.step_swing(dt=0.016, x=x, y=y, vx=vx, vy=vy)
            self.assertIsInstance(x, float)
            self.assertIsInstance(y, float)
            self.assertIsInstance(tilt, float)
            self.assertIsInstance(finished, bool)

    def test_web_ghosts(self):
        self.web.web_anchor_x = 200.0
        self.web.web_anchor_y = 100.0
        self.web.push_web_ghost(hx=220.0, hy=300.0)
        self.assertEqual(len(self.web.web_ghosts), 1)
        self.assertIn("a", self.web.web_ghosts[0])

if __name__ == "__main__":
    unittest.main()
