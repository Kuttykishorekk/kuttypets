"""
KuttyPets - Cross-Platform Dynamic Desktop Companion.
Main Entrypoint with automatic OS discovery and adapter selection.
"""

from __future__ import annotations
import sys
import os
import argparse
from pathlib import Path
from typing import Optional

# Ensure stdout/stderr are valid streams on Windows windowed mode (console=False)
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

# Ensure package root is in sys.path when bundled by PyInstaller as standalone script
pkg_dir = Path(__file__).resolve().parent
if str(pkg_dir.parent) not in sys.path:
    sys.path.insert(0, str(pkg_dir.parent))
if str(pkg_dir) not in sys.path:
    sys.path.insert(0, str(pkg_dir))

try:
    from kuttypets.config import discover_characters, PRESENCE_PROFILES
    from kuttypets.core.rigs import SpriteRigAnalyzer
    from kuttypets.core.engine import OmniPetEngine
    from kuttypets.adapters.base import BaseWindowAdapter
    from kuttypets.core.autostart import AutostartManager
except ImportError:
    from config import discover_characters, PRESENCE_PROFILES
    from core.rigs import SpriteRigAnalyzer
    from core.engine import OmniPetEngine
    from adapters.base import BaseWindowAdapter
    from core.autostart import AutostartManager

_single_instance_handle = None

def acquire_single_instance_lock() -> bool:
    """Prevents multiple duplicate companion instances from running on the desktop."""
    global _single_instance_handle
    if sys.platform == "win32":
        try:
            import ctypes
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\KuttyPets_SingleInstance_Mutex")
            ERROR_ALREADY_EXISTS = 183
            if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
                return False
            _single_instance_handle = mutex
            return True
        except Exception:
            return True
    return True

def create_adapter() -> BaseWindowAdapter:
    """Instantiates the best window and display adapter for the current operating system."""
    if sys.platform == "darwin":
        try:
            from kuttypets.adapters.mac_cocoa import MacOSCocoaAdapter
        except ImportError:
            from adapters.mac_cocoa import MacOSCocoaAdapter
        print("[KuttyPets] Initializing macOS Cocoa / Quartz Adapter...", flush=True)
        return MacOSCocoaAdapter()
    elif sys.platform == "win32":
        try:
            from kuttypets.adapters.win32_adapter import Win32Adapter
        except ImportError:
            from adapters.win32_adapter import Win32Adapter
        print("[KuttyPets] Initializing Windows Win32 / DWM Adapter...", flush=True)
        return Win32Adapter()
    else:
        try:
            from kuttypets.adapters.linux_hyprland import LinuxHyprlandAdapter
        except ImportError:
            from adapters.linux_hyprland import LinuxHyprlandAdapter
        print("[KuttyPets] Initializing Linux Hyprland / Wayland Adapter...", flush=True)
        return LinuxHyprlandAdapter()

def main():
    parser = argparse.ArgumentParser(description="KuttyPets - Dynamic Desktop Companion")
    parser.add_argument("--character", "-c", default="spiderman", help="Character ID (spiderman, hutao, klee, ayaka, venti)")
    parser.add_argument("--mode", "-m", default="calm", choices=["calm", "lively", "stealth"], help="Presence mode")
    parser.add_argument("--scale", "-s", type=float, default=0.68, help="Render scale (default 0.68)")
    parser.add_argument("--debug", action="store_true", help="Enable visual physics gizmos and live telemetry HUD")
    parser.add_argument("--list-characters", action="store_true", help="List all available characters")
    parser.add_argument("--headless-check", "--test", action="store_true", help="Run automated headless self-test and exit")
    parser.add_argument("--autostart-enable", action="store_true", help="Enable automatic start on system boot/login")
    parser.add_argument("--autostart-disable", action="store_true", help="Disable automatic start on system boot/login")
    parser.add_argument("--autostart-status", action="store_true", help="Check if autostart on boot is currently enabled")
    args = parser.parse_args()

    # Prevent multiple duplicate instances running simultaneously
    if not acquire_single_instance_lock():
        print("[KuttyPets] Another instance is already running on this desktop. Exiting.", flush=True)
        return

    # Handle Autostart management
    if args.autostart_enable:
        success = AutostartManager.set_enabled(True)
        print(f"[KuttyPets] Autostart on boot: {'ENABLED' if success else 'FAILED'}", flush=True)
        return
    elif args.autostart_disable:
        success = AutostartManager.set_enabled(False)
        print(f"[KuttyPets] Autostart on boot: {'DISABLED' if success else 'FAILED'}", flush=True)
        return
    elif args.autostart_status:
        status = AutostartManager.is_enabled()
        print(f"[KuttyPets] Autostart on boot status: {'ENABLED' if status else 'DISABLED'}", flush=True)
        return

    # Discover characters
    characters = discover_characters()
    if args.list_characters:
        print("\nAvailable Characters:")
        for cid, meta in characters.items():
            print(f"  - {cid:12s} ({meta.get('name', cid)}) [{meta.get('frame_count', 0)} frames]")
        return

    if args.character not in characters:
        print(f"[KuttyPets] Character '{args.character}' not found. Available: {list(characters.keys())}")
        if "spiderman" in characters:
            args.character = "spiderman"
        elif characters:
            args.character = list(characters.keys())[0]

    adapter = create_adapter()
    engine = OmniPetEngine(
        adapter=adapter,
        char_id=args.character,
        presence_mode=args.mode,
        render_scale=args.scale,
    )

    # Load and rig character frames
    char_dir = characters[args.character]["path"]
    rigs = SpriteRigAnalyzer.load_and_rig_character(char_dir)
    engine.set_character_rigs(rigs)
    print(f"[KuttyPets] Rigged {len(rigs)} sprite frames for '{args.character}'.", flush=True)

    # Print screen and layout metrics
    screen = adapter.get_screen_geometry()
    metrics = adapter.get_layout_metrics()
    print(f"[KuttyPets] Display: {screen['width']}x{screen['height']} (scale={screen.get('scale', 1.0)}) | Layout: rounding={metrics.get('rounding')}, border={metrics.get('border_size')}", flush=True)

    # Handle Headless Self-Test verification
    if args.headless_check:
        print("[KuttyPets] Executing headless self-test loop...", flush=True)
        assert len(characters) > 0, "No characters discovered"
        assert len(rigs) > 0, f"No sprite rigs loaded for {args.character}"
        for step in range(25):
            engine.tick()
        autostart_stat = AutostartManager.is_enabled()
        print(f"[KuttyPets] Engine state after 25 ticks: {engine.state} at ({engine.x:.1f}, {engine.y:.1f})")
        print(f"[KuttyPets] Autostart test query: {autostart_stat}")
        print("[KuttyPets] Headless self-test PASSED successfully.", flush=True)
        return

    # Launch cross-platform GUI overlay
    try:
        from PyQt6.QtWidgets import QApplication
        try:
            from kuttypets.render.canvas import KuttyPetsOverlay
        except ImportError:
            from render.canvas import KuttyPetsOverlay

        app = QApplication(sys.argv)
        app.setApplicationName("KuttyPets")
        overlay = KuttyPetsOverlay(engine, char_dir, debug_mode=args.debug)
        sys.exit(app.exec())
    except Exception as e:
        print(f"[KuttyPets] PyQt6 overlay unavailable ({e}); running headless engine loop.", flush=True)
        try:
            while True:
                engine.tick()
                import time
                time.sleep(0.016)
        except KeyboardInterrupt:
            print("[KuttyPets] Exiting cleanly.", flush=True)

if __name__ == "__main__":
    main()
