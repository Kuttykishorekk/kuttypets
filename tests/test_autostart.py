"""
Tests for autostart manager resolution and platform commands.
"""

import sys
import unittest
from kuttypets.core.autostart import AutostartManager

class TestAutostartManager(unittest.TestCase):
    def test_get_executable_command(self):
        cmd = AutostartManager.get_executable_command()
        self.assertIsInstance(cmd, str)
        self.assertGreater(len(cmd), 0)

    def test_is_enabled_query(self):
        # Should not throw exception regardless of platform
        status = AutostartManager.is_enabled()
        self.assertIsInstance(status, bool)

    def test_linux_desktop_path(self):
        if sys.platform not in ("win32", "darwin"):
            path = AutostartManager._get_linux_desktop_path()
            self.assertIn("autostart", path)
            self.assertTrue(path.endswith("kuttypets.desktop"))

if __name__ == "__main__":
    unittest.main()
