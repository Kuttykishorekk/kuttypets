"""
OmniPet - Cross-Platform Dynamic Desktop Pet Companion Engine
Configuration, Character Registry, and Dynamic Presence Profiles.
"""

from __future__ import annotations
import os
import sys
from typing import Dict, Any, List

# Presence profiles dictate the behavior, activity cadence, and energy level
PRESENCE_PROFILES: Dict[str, Dict[str, Any]] = {
    "calm": {
        "rest_bias": 0.88,
        "climb_speed": 40.0,
        "walk_speed": 48.0,
        "cling_duration": (6.0, 16.0),
        "wall_rest": (2.0, 5.5),
        "idle_sit": (3.5, 9.0),
        "perch_interval": 14.0,
        "leap_chance": 0.08,
        "slide_particle": 0.06,
        "sway": 0.55,
        "max_particles": 6,
        "idle_alpha": 0.94,
        "active_alpha": 1.0,
    },
    "lively": {
        "rest_bias": 0.35,
        "climb_speed": 58.0,
        "walk_speed": 66.0,
        "cling_duration": (3.5, 9.0),
        "wall_rest": (1.0, 2.8),
        "idle_sit": (1.8, 4.5),
        "perch_interval": 7.0,
        "leap_chance": 0.28,
        "slide_particle": 0.16,
        "sway": 0.85,
        "max_particles": 12,
        "idle_alpha": 0.98,
        "active_alpha": 1.0,
    },
    "stealth": {
        "rest_bias": 0.96,
        "climb_speed": 34.0,
        "walk_speed": 38.0,
        "cling_duration": (10.0, 26.0),
        "wall_rest": (4.0, 10.0),
        "idle_sit": (6.0, 16.0),
        "perch_interval": 24.0,
        "leap_chance": 0.03,
        "slide_particle": 0.02,
        "sway": 0.35,
        "max_particles": 3,
        "idle_alpha": 0.82,
        "active_alpha": 0.96,
    },
}

# Character metadata templates
CHARACTER_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "spiderman": {
        "name": "Spider-Man",
        "format": "shimeji",
        "raw_facing": "LEFT",
        "climb_raw_facing": "LEFT",
        "particle": "sparkle",
        "can_swing": True,
        "web_color": (0.95, 0.96, 1.0, 0.92),
    },
    "hutao": {
        "name": "Hu Tao",
        "format": "genshin",
        "raw_facing": "RIGHT",
        "climb_raw_facing": "RIGHT",
        "particle": "butterfly",
        "can_swing": False,
    },
    "klee": {
        "name": "Klee",
        "format": "genshin",
        "raw_facing": "RIGHT",
        "climb_raw_facing": "RIGHT",
        "particle": "clover",
        "can_swing": False,
    },
    "ayaka": {
        "name": "Kamisato Ayaka",
        "format": "genshin",
        "raw_facing": "RIGHT",
        "climb_raw_facing": "RIGHT",
        "particle": "sakura",
        "can_swing": False,
    },
    "venti": {
        "name": "Venti",
        "format": "genshin",
        "raw_facing": "RIGHT",
        "climb_raw_facing": "RIGHT",
        "particle": "feather",
        "can_swing": False,
    },
}

def get_base_characters_dir() -> str:
    """Resolve character asset directory dynamically across dev, installed, and frozen PyInstaller environments."""
    # 1. Check if running inside PyInstaller bundle (sys._MEIPASS)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        for sub in ("kuttypets/characters", "characters"):
            bundle_dir = os.path.join(sys._MEIPASS, sub)
            if os.path.isdir(bundle_dir):
                return bundle_dir

    # 2. Check local package directory
    local_pkg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")
    if os.path.isdir(local_pkg) and any(os.path.isdir(os.path.join(local_pkg, d)) for d in os.listdir(local_pkg)):
        return local_pkg
    
    # 3. Check user data directories
    if sys.platform == "darwin":
        user_dir = os.path.expanduser("~/Library/Application Support/kuttypets/characters")
    elif sys.platform == "win32":
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        user_dir = os.path.join(app_data, "kuttypets", "characters")
    else:
        user_dir = os.path.expanduser("~/.local/share/kuttypets")
        if not os.path.isdir(user_dir):
            user_dir = os.path.expanduser("~/.local/share/hyprpet")
    
    if os.path.isdir(user_dir):
        return user_dir
    
    return local_pkg

def discover_characters(base_dir: str | None = None) -> Dict[str, Dict[str, Any]]:
    """Dynamically discover character folders and their frame metadata."""
    if base_dir is None:
        base_dir = get_base_characters_dir()
    
    registry: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(base_dir):
        return registry
    
    for entry in sorted(os.listdir(base_dir)):
        cdir = os.path.join(base_dir, entry)
        if not os.path.isdir(cdir):
            continue
        
        # Check if directory contains PNG frames
        pngs = [f for f in os.listdir(cdir) if f.endswith(".png")]
        if not pngs:
            continue
        
        # Determine format (shimeji has shime1.png, genshin has id1_1.png / sp1_1.png)
        if any(f.startswith("shime") for f in pngs):
            fmt = "shimeji"
            def_facing = "LEFT"
        else:
            fmt = "genshin"
            def_facing = "RIGHT"
        
        template = CHARACTER_TEMPLATES.get(entry, {
            "name": entry.capitalize(),
            "format": fmt,
            "raw_facing": def_facing,
            "climb_raw_facing": def_facing,
            "particle": "sparkle",
            "can_swing": (fmt == "shimeji"),
        })
        
        registry[entry] = {
            **template,
            "id": entry,
            "path": cdir,
            "frame_count": len(pngs),
        }
        
    return registry
