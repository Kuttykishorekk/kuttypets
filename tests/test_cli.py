"""
Tests for CLI invocation and subcommands.
"""

import sys
import subprocess
import unittest

class TestCLI(unittest.TestCase):
    def test_cli_list_characters(self):
        res = subprocess.run(
            [sys.executable, "-m", "kuttypets.main", "--list-characters"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("spiderman", res.stdout)

    def test_cli_headless_check(self):
        res = subprocess.run(
            [sys.executable, "-m", "kuttypets.main", "--headless-check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Headless self-test PASSED successfully", res.stdout)

    def test_cli_autostart_status(self):
        res = subprocess.run(
            [sys.executable, "-m", "kuttypets.main", "--autostart-status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Autostart on boot status", res.stdout)

if __name__ == "__main__":
    unittest.main()
