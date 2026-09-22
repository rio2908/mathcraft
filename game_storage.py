"""Low-level local persistence for MathCraft."""

import json
import os


SAVE_FILE = "mc_math_save.json"
LAST_PLAYER_FILE = "mc_last_player.txt"


def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as save_file:
                return json.load(save_file)
        except Exception:
            return {}
    return {}


def save_data(data):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as save_file:
            json.dump(data, save_file, ensure_ascii=False, indent=4)
    except Exception:
        pass


def get_last_player():
    if os.path.exists(LAST_PLAYER_FILE):
        try:
            with open(LAST_PLAYER_FILE, "r", encoding="utf-8") as last_player_file:
                name = last_player_file.read().strip()
                if name:
                    return name
        except Exception:
            return None
    return None


def set_last_player(name):
    try:
        with open(LAST_PLAYER_FILE, "w", encoding="utf-8") as last_player_file:
            last_player_file.write(name.strip())
    except Exception:
        pass
