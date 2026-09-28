"""
Tests for OmniPet engine loop, state machine transitions, and rig integration.
"""

import unittest
from typing import List, Dict, Any, Optional
from kuttypets.adapters.base import BaseWindowAdapter, WindowInfo
from kuttypets.core.engine import OmniPetEngine
from kuttypets.config import discover_characters
from kuttypets.core.rigs import SpriteRigAnalyzer

class MockWindowAdapter(BaseWindowAdapter):
    """Platform-independent mock adapter for automated headless unit testing."""

    def __init__(self):
        self.windows = [
            WindowInfo(
                address="0x1000",
                x1=100.0,
                x2=900.0,
                y_top=100.0,
                y_bot=700.0,
                title="Code Editor",
                app_class="code",
                is_active=True,
                is_floating=False,
            )
        ]

    def get_windows(self) -> List[WindowInfo]:
        return self.windows

    def get_active_window(self) -> Optional[WindowInfo]:
        return self.windows[0] if self.windows else None

    def get_screen_geometry(self) -> Dict[str, float]:
        return {"x": 0.0, "y": 0.0, "width": 1920.0, "height": 1080.0, "scale": 1.0}

    def get_layout_metrics(self) -> Dict[str, float]:
        return {"rounding": 12.0, "border_size": 2.0, "gap_top": 8.0, "gap_bottom": 4.0}

class TestOmniPetEngine(unittest.TestCase):
    def setUp(self):
        self.adapter = MockWindowAdapter()
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

    def test_engine_initialization(self):
        self.assertEqual(self.engine.current_char, "spiderman")
        self.assertEqual(self.engine.presence_mode, "lively")
        self.assertEqual(self.engine.state, "SITTING")

    def test_engine_tick_simulation(self):
        # Step engine 50 physics ticks
        initial_time = self.engine.last_time
        for _ in range(50):
            self.engine.tick()

        self.assertGreaterEqual(self.engine.last_time, initial_time)
        self.assertIsInstance(self.engine.x, float)
        self.assertIsInstance(self.engine.y, float)
        self.assertIsInstance(self.engine.state, str)

    def test_engine_drag_interaction(self):
        self.engine.start_drag(500.0, 400.0)
        self.assertTrue(self.engine.is_dragging)
        self.assertEqual(self.engine.state, "DRAGGING")

        self.engine.update_drag(550.0, 420.0)
        self.assertEqual(self.engine.x, 550.0 - self.engine.drag_offset_x)

        self.engine.end_drag()
        self.assertFalse(self.engine.is_dragging)
        self.assertEqual(self.engine.state, "FALLING")

    def test_multi_character_alignments(self):
        chars = discover_characters()
        for cid in ("hutao", "klee", "ayaka", "venti", "spiderman"):
            if cid not in chars:
                continue
            eng = OmniPetEngine(self.adapter, char_id=cid, render_scale=0.68)
            rigs = SpriteRigAnalyzer.load_and_rig_character(chars[cid]["path"])
            eng.set_character_rigs(rigs)

            # 1. Floor / Top stand Y calculation
            stand_y = eng.compute_stand_y(500.0)
            self.assertLess(stand_y, 500.0, f"Stand Y for {cid} must be above surface")
            self.assertGreater(stand_y, 400.0, f"Stand Y for {cid} must be reasonably near surface")

            # 2. Left wall cling X calculation
            left_cling_x = eng.compute_outward_cling_x(100.0, "LEFT")
            self.assertLess(left_cling_x, 100.0, f"Left wall cling X for {cid} must be outside window to the left")

            # 3. Right wall cling X calculation
            right_cling_x = eng.compute_outward_cling_x(900.0, "RIGHT")
            self.assertGreater(right_cling_x, 900.0, f"Right wall cling X for {cid} must be outside window to the right")

            # 4. Hand reach must be positive and non-zero
            hand_reach = eng.get_climb_hand_reach()
            self.assertGreater(hand_reach, 0.0, f"Hand reach for {cid} must be positive")

if __name__ == "__main__":
    unittest.main()
