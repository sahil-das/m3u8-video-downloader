# settings.py
import json
import os

SETTINGS_FILE = "settings.json"

DEFAULTS = {
    "theme": "dark",
    "num_connections": 3,
    "segment_threads": 8,
    "output_dir": "",
    "notifications": True
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULTS)
        return DEFAULTS.copy()

    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        # fill in missing keys
        for key, val in DEFAULTS.items():
            settings.setdefault(key, val)
        return settings
    except:
        return DEFAULTS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
