"""
Tests for sprite alpha analysis and biomechanical rig extraction.
"""

import os
import unittest
from PIL import Image
from kuttypets.config import discover_characters
from kuttypets.core.rigs import SpriteRigAnalyzer

class TestSpriteRigAnalyzer(unittest.TestCase):
    def test_measure_synthetic_sprite_grip(self):
        # Create a synthetic 100x100 RGBA image with a solid rectangle
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        # Draw a solid center box (x: 30..70, y: 30..80)
        for x in range(30, 70):
            for y in range(30, 80):
                img.putpixel((x, y), (255, 0, 0, 255))

        grip_l, grip_r, grip_t, grip_b = SpriteRigAnalyzer.measure_sprite_grip(img)
        self.assertGreaterEqual(grip_l, 25)
        self.assertLessEqual(grip_r, 75)
        self.assertGreaterEqual(grip_t, 25)
        self.assertLessEqual(grip_b, 85)

    def test_load_and_rig_character(self):
        chars = discover_characters()
        self.assertIn("spiderman", chars)
        char_dir = chars["spiderman"]["path"]
        
        rigs = SpriteRigAnalyzer.load_and_rig_character(char_dir)
        self.assertIsInstance(rigs, dict)
        self.assertGreater(len(rigs), 0, "Spider-Man rigs should have loaded frames")

        first_key = next(iter(rigs))
        rig = rigs[first_key]
        self.assertIn("width", rig)
        self.assertIn("height", rig)
        self.assertIn("left_reach", rig)
        self.assertIn("right_reach", rig)
        self.assertIn("grip_left_reach", rig)
        self.assertIn("grip_right_reach", rig)
        self.assertIn("top_reach", rig)
        self.assertIn("bottom_reach", rig)
        self.assertIn("grip_top_reach", rig)
        self.assertIn("grip_bottom_reach", rig)

if __name__ == "__main__":
    unittest.main()
