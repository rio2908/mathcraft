"""Low-level local persistence for MathCraft."""

import json
import os
import sys
import tempfile


SAVE_FILE = "mc_math_save.json"
LAST_PLAYER_FILE = "mc_last_player.txt"
BACKUP_FORMAT = "mathcraft-backup"
BACKUP_VERSION = 1
MAX_BACKUP_BYTES = 10 * 1024 * 1024


def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as save_file:
                return json.load(save_file)
        except Exception:
            return {}
    return {}


def save_data(data):
    temporary_path = None
    try:
        if sys.platform == "emscripten":
            # BrowserFS does not guarantee support for atomic os.replace().
            with open(SAVE_FILE, "w", encoding="utf-8") as save_file:
                json.dump(data, save_file, ensure_ascii=False, indent=4)
            return
        save_dir = os.path.dirname(os.path.abspath(SAVE_FILE))
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=save_dir,
            prefix=".mc_math_save-", suffix=".tmp", delete=False,
        ) as save_file:
            temporary_path = save_file.name
            json.dump(data, save_file, ensure_ascii=False, indent=4)
        os.replace(temporary_path, SAVE_FILE)
        temporary_path = None
    except Exception:
        pass
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
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


def make_backup_bytes():
    """Export every profile and the selected player as a portable JSON file."""
    profiles = load_data()
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("Нет сохранённых игроков для копирования.")
    document = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "profiles": profiles,
        "last_player": get_last_player(),
    }
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")


def restore_backup_bytes(content):
    """Import missing profiles without overwriting progress already on device."""
    if len(content) > MAX_BACKUP_BYTES:
        raise ValueError("Файл резервной копии слишком большой.")
    try:
        document = json.loads(content.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise ValueError("Не удалось прочитать файл резервной копии.") from error
    if not isinstance(document, dict) or document.get("format") != BACKUP_FORMAT or document.get("version") != BACKUP_VERSION:
        raise ValueError("Это не резервная копия MathCraft.")
    incoming = document.get("profiles")
    if not isinstance(incoming, dict) or not incoming or any(
        not isinstance(name, str) or not name.strip() or not isinstance(profile, dict)
        for name, profile in incoming.items()
    ):
        raise ValueError("В копии нет корректных профилей игроков.")
    existing = load_data()
    if not isinstance(existing, dict):
        existing = {}
    added = 0
    for name, profile in incoming.items():
        if name not in existing:
            existing[name] = profile
            added += 1
    if added:
        save_data(existing)
        if load_data() != existing:
            raise OSError("Не удалось сохранить восстановленные профили.")
    last_player = document.get("last_player")
    if get_last_player() not in existing and isinstance(last_player, str) and last_player in existing:
        set_last_player(last_player)
    return added, len(incoming) - added
