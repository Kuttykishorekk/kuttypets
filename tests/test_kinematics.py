"""
Tests for kinematics, corner geometry, quintic smoothing and gait computations.
"""

import math
import unittest
from kuttypets.core.kinematics import KinematicsEngine

class TestKinematicsEngine(unittest.TestCase):
    def test_edge_end_factor(self):
        # Center of window (far from edge) -> factor 1.0
        factor_mid = KinematicsEngine.edge_end_factor(pos=500, start=100, end=900, travel_dir=1.0, slow_dist=72.0)
        self.assertEqual(factor_mid, 1.0)

        # Right at the edge end -> factor 0.0
        factor_end = KinematicsEngine.edge_end_factor(pos=898, start=100, end=900, travel_dir=1.0, slow_dist=72.0)
        self.assertEqual(factor_end, 0.0)

        # In deceleration zone (e.g. 36px from end) -> 0 < factor < 1
        factor_decel = KinematicsEngine.edge_end_factor(pos=864, start=100, end=900, travel_dir=1.0, slow_dist=72.0)
        self.assertTrue(0.0 < factor_decel < 1.0)

    def test_compute_stride_gait(self):
        phase, plant, smul = KinematicsEngine.compute_stride_gait(tick=1.0, speed=10.0, cadence=14.0)
        self.assertIsInstance(phase, float)
        self.assertGreaterEqual(plant, 0.0)
        self.assertGreaterEqual(smul, 0.5)

    def test_compute_corner_geometry(self):
        fake_win = {
            "x1": 100.0,
            "x2": 600.0,
            "y_top": 200.0,
            "y_bot": 700.0,
        }
        spec = KinematicsEngine.compute_corner_geometry(
            win=fake_win,
            from_side="RIGHT",
            to_side="TOP",
            render_scale=0.68,
            hypr_rounding=20.0,
            hypr_border_size=2.0,
        )
        self.assertIsNotNone(spec)
        self.assertIn("cx", spec)
        self.assertIn("cy", spec)
        self.assertIn("a0", spec)
        self.assertIn("a1", spec)

        # Test evaluating corner step
        step_res = KinematicsEngine.evaluate_corner_step(u=0.5, dt=0.016, meta=spec, render_scale=0.68)
        self.assertIn("x", step_res)
        self.assertIn("y", step_res)
        self.assertIn("scale_x", step_res)
        self.assertIn("scale_y", step_res)

if __name__ == "__main__":
    unittest.main()
