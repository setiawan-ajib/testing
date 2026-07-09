import json
import os
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent 
SETTINGS_FILE = _BASE_DIR / "last_settings.json"

def save_settings(config_values: dict, lane_lka_values: dict) -> bool:
    try:
        data = {
            "config": config_values,
            "lane_lka": lane_lka_values,
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[SETTINGS] Saved OK → {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"[SETTINGS] SAVE FAILED: {e}")
        return False

def load_settings() -> dict | None:
    if not SETTINGS_FILE.exists():
        print(f"[SETTINGS] File belum ada: {SETTINGS_FILE}")
        return None
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        print(f"[SETTINGS] Loaded OK ← {SETTINGS_FILE}")
        return data
    except Exception as e:
        print(f"[SETTINGS] LOAD FAILED: {e}")
        return None