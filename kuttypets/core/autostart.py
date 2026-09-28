"""
KuttyPets - Cross-Platform Autostart & System Startup Manager.
Supports Windows Registry (HKCU/Run), macOS LaunchAgents (plist), and Linux XDG Autostart (.desktop).
"""

from __future__ import annotations
import sys
import os
from typing import Optional

class AutostartManager:
    """Manages boot/login autostart persistence dynamically across Linux, macOS, and Windows."""

    APP_NAME = "KuttyPets"
    APP_ID = "com.kutty.kuttypets"

    @classmethod
    def get_executable_command(cls) -> str:
        """Resolves the exact command or path to run this application."""
        if getattr(sys, "frozen", False):
            # PyInstaller binary
            return os.path.abspath(sys.executable)
        else:
            # Running as python module/script
            main_script = os.path.abspath(sys.argv[0])
            return f'"{sys.executable}" "{main_script}"'

    # ------------------------------------------------------------------
    # Windows Implementation (HKCU\Software\Microsoft\Windows\CurrentVersion\Run)
    # ------------------------------------------------------------------
    @classmethod
    def _is_enabled_windows(cls) -> bool:
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, cls.APP_NAME)
                return True
        except Exception:
            return False

    @classmethod
    def _set_enabled_windows(cls, enable: bool) -> bool:
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    cmd = f'"{cls.get_executable_command()}"'
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, cls.APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception as e:
            print(f"[KuttyPets] Error updating Windows autostart: {e}", flush=True)
            return False

    # ------------------------------------------------------------------
    # macOS Implementation (~/Library/LaunchAgents/com.kutty.kuttypets.plist)
    # ------------------------------------------------------------------
    @classmethod
    def _get_macos_plist_path(cls) -> str:
        agents_dir = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(agents_dir, exist_ok=True)
        return os.path.join(agents_dir, f"{cls.APP_ID}.plist")

    @classmethod
    def _is_enabled_macos(cls) -> bool:
        return os.path.isfile(cls._get_macos_plist_path())

    @classmethod
    def _set_enabled_macos(cls, enable: bool) -> bool:
        plist_path = cls._get_macos_plist_path()
        if not enable:
            if os.path.isfile(plist_path):
                try:
                    os.remove(plist_path)
                except Exception:
                    pass
            return True

        cmd = cls.get_executable_command()
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{cls.APP_ID}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{cmd}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        try:
            with open(plist_path, "w", encoding="utf-8") as f:
                f.write(plist_content)
            return True
        except Exception as e:
            print(f"[KuttyPets] Error writing macOS LaunchAgent: {e}", flush=True)
            return False

    # ------------------------------------------------------------------
    # Linux Implementation (~/.config/autostart/kuttypets.desktop)
    # ------------------------------------------------------------------
    @classmethod
    def _get_linux_desktop_path(cls) -> str:
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        return os.path.join(autostart_dir, "kuttypets.desktop")

    @classmethod
    def _is_enabled_linux(cls) -> bool:
        return os.path.isfile(cls._get_linux_desktop_path())

    @classmethod
    def _set_enabled_linux(cls, enable: bool) -> bool:
        path = cls._get_linux_desktop_path()
        if not enable:
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            return True

        cmd = cls.get_executable_command()
        desktop_content = f"""[Desktop Entry]
Type=Application
Exec={cmd}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=KuttyPets
Comment=Dynamic Desktop Pet Companion with Real Biomechanical Physics
Icon=kuttypets
"""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            return True
        except Exception as e:
            print(f"[KuttyPets] Error writing Linux autostart file: {e}", flush=True)
            return False

    # ------------------------------------------------------------------
    # Universal Cross-Platform Public API
    # ------------------------------------------------------------------
    @classmethod
    def is_enabled(cls) -> bool:
        """Checks if autostart on boot is currently enabled for the current user."""
        if sys.platform == "win32":
            return cls._is_enabled_windows()
        elif sys.platform == "darwin":
            return cls._is_enabled_macos()
        else:
            return cls._is_enabled_linux()

    @classmethod
    def set_enabled(cls, enable: bool) -> bool:
        """Enables or disables autostart on boot."""
        if sys.platform == "win32":
            return cls._set_enabled_windows(enable)
        elif sys.platform == "darwin":
            return cls._set_enabled_macos(enable)
        else:
            return cls._set_enabled_linux(enable)

    @classmethod
    def toggle(cls) -> bool:
        """Toggles the current autostart state and returns the new state."""
        new_state = not cls.is_enabled()
        cls.set_enabled(new_state)
        return new_state
