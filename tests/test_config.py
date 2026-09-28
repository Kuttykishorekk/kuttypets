"""
Tests for configuration and character asset discovery.
"""

import os
import unittest
from kuttypets.config import discover_characters, PRESENCE_PROFILES, CHARACTER_TEMPLATES, get_base_characters_dir

class TestConfig(unittest.TestCase):
    def test_base_characters_dir_exists(self):
        chars_dir = get_base_characters_dir()
        self.assertTrue(os.path.isdir(chars_dir), f"Base characters dir does not exist: {chars_dir}")

    def test_discover_characters(self):
        chars = discover_characters()
        self.assertIsInstance(chars, dict)
        self.assertGreaterEqual(len(chars), 1, "At least one character must be discovered")
        self.assertIn("spiderman", chars, "Spider-Man character profile must be present")
        
        spidey = chars["spiderman"]
        self.assertIn("path", spidey)
        self.assertIn("frame_count", spidey)
        self.assertGreater(spidey["frame_count"], 0)

    def test_presence_profiles(self):
        self.assertIn("calm", PRESENCE_PROFILES)
        self.assertIn("lively", PRESENCE_PROFILES)
        self.assertIn("stealth", PRESENCE_PROFILES)
        for mode, profile in PRESENCE_PROFILES.items():
            self.assertIn("rest_bias", profile)
            self.assertIn("climb_speed", profile)
            self.assertIn("walk_speed", profile)
            self.assertIn("cling_duration", profile)
            self.assertIn("leap_chance", profile)

    def test_character_templates(self):
        self.assertIn("spiderman", CHARACTER_TEMPLATES)
        self.assertIn("hutao", CHARACTER_TEMPLATES)
        self.assertIn("klee", CHARACTER_TEMPLATES)

if __name__ == "__main__":
    unittest.main()
