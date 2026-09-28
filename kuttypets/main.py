"""
OmniPet - Cross-Platform Dynamic Desktop Companion.
Main Entrypoint with automatic OS discovery and adapter selection.
"""

from __future__ import annotations
import sys
import os
import argparse
from typing import Optional

from .config import discover_characters, PRESENCE_PROFILES
from .core.rigs import SpriteRigAnalyzer
from .core.engine import OmniPetEngine
from .adapters.base import BaseWindowAdapter

def create_adapter() -> BaseWindowAdapter:
    """Instantiates the best window and display adapter for the current operating system."""
    if sys.platform == "darwin":
        from .adapters.mac_cocoa import MacOSCocoaAdapter
        print("[KuttyPets] Initializing macOS Cocoa / Quartz Adapter...", flush=True)
        return MacOSCocoaAdapter()
    elif sys.platform == "win32":
        from .adapters.win32_adapter import Win32Adapter
        print("[KuttyPets] Initializing Windows Win32 / DWM Adapter...", flush=True)
        return Win32Adapter()
    else:
        from .adapters.linux_hyprland import LinuxHyprlandAdapter
        print("[KuttyPets] Initializing Linux Hyprland / Wayland Adapter...", flush=True)
        return LinuxHyprlandAdapter()

def main():
    parser = argparse.ArgumentParser(description="OmniPet - Dynamic Desktop Companion")
    parser.add_argument("--character", "-c", default="spiderman", help="Character ID (spiderman, hutao, klee, ayaka, venti)")
    parser.add_argument("--mode", "-m", default="calm", choices=["calm", "lively", "stealth"], help="Presence mode")
    parser.add_argument("--scale", "-s", type=float, default=0.68, help="Render scale (default 0.68)")
    parser.add_argument("--list-characters", action="store_true", help="List all available characters")
    args = parser.parse_args()

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

    # In Linux GTK / PyGObject environment:
    if sys.platform.startswith("linux"):
        import gi
        gi.require_version("Gtk", "3.0")
        try:
            gi.require_version("GtkLayerShell", "0.1")
            from gi.repository import GtkLayerShell
        except Exception:
            GtkLayerShell = None
        from gi.repository import Gtk, GLib

        # Link engine tick to GTK main loop
        def _gtk_tick():
            engine.tick()
            return True

        GLib.timeout_add(16, _gtk_tick)
        print("[KuttyPets] Engine loop running. Press Ctrl+C to stop.", flush=True)
        # Note: If running with full UI window, HyprPet overlay class integrates directly with engine
    else:
        print(f"[KuttyPets] Running on {sys.platform}. Core engine initialized successfully.", flush=True)

if __name__ == "__main__":
    main()
