import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import game_storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.save_path = temp_path / "mc_math_save.json"
        self.last_player_path = temp_path / "mc_last_player.txt"
        self.patches = [
            patch.object(game_storage, "SAVE_FILE", str(self.save_path)),
            patch.object(
                game_storage,
                "LAST_PLAYER_FILE",
                str(self.last_player_path),
            ),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def test_profiles_round_trip_with_unicode_names(self):
        profiles = {
            "Ксения": {"emeralds": 17},
            "Настя": {"emeralds": 31},
        }
        game_storage.save_data(profiles)
        self.assertEqual(game_storage.load_data(), profiles)
        self.assertEqual(
            json.loads(self.save_path.read_text(encoding="utf-8")),
            profiles,
        )

    def test_last_player_round_trip_strips_whitespace(self):
        game_storage.set_last_player("  Ксения  ")
        self.assertEqual(game_storage.get_last_player(), "Ксения")

    def test_missing_files_have_empty_defaults(self):
        self.assertEqual(game_storage.load_data(), {})
        self.assertIsNone(game_storage.get_last_player())

    def test_corrupt_save_is_treated_as_empty(self):
        self.save_path.write_text("{broken json", encoding="utf-8")
        self.assertEqual(game_storage.load_data(), {})


if __name__ == "__main__":
    unittest.main()
