import json
import os

SETTINGS_FILE = "m3u8_downloader_settings.json"

DEFAULTS = {
    "output_dir": "",
    "num_connections": 8,
    "max_parallel": 5,
    "ffmpeg_path": "ffmpeg",
    "theme": "dark",
    "enable_notifications": True 
}

VALID_THREADS = [1, 2, 4, 8, 16, 32]
MIN_PARALLEL = 1
MAX_PARALLEL = 10

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULTS)
        return DEFAULTS.copy()

    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)

        # Fill missing keys with defaults
        for key, val in DEFAULTS.items():
            settings.setdefault(key, val)

        # Validate num_connections
        if settings.get("num_connections") not in VALID_THREADS:
            settings["num_connections"] = DEFAULTS["num_connections"]

        # Validate max_parallel
        max_par = settings.get("max_parallel")
        if not isinstance(max_par, int) or not (MIN_PARALLEL <= max_par <= MAX_PARALLEL):
            settings["max_parallel"] = DEFAULTS["max_parallel"]

        # Optionally save corrected settings
        save_settings(settings)

        return settings
    except Exception:
        return DEFAULTS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
