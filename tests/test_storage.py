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

    def test_read_during_save_sees_complete_previous_version(self):
        old_profiles = {"Тест": {"emeralds": 10}}
        new_profiles = {"Тест": {"emeralds": 20}}
        game_storage.save_data(old_profiles)
        original_dump = json.dump
        observations = []

        def inspect_partial_write(value, stream, **kwargs):
            stream.write("{")
            stream.flush()
            observations.append(game_storage.load_data())
            stream.seek(0)
            stream.truncate()
            original_dump(value, stream, **kwargs)

        with patch.object(game_storage.json, "dump", side_effect=inspect_partial_write):
            game_storage.save_data(new_profiles)
        self.assertEqual(observations, [old_profiles])
        self.assertEqual(game_storage.load_data(), new_profiles)

    def test_last_player_round_trip_strips_whitespace(self):
        game_storage.set_last_player("  Ксения  ")
        self.assertEqual(game_storage.get_last_player(), "Ксения")

    def test_missing_files_have_empty_defaults(self):
        self.assertEqual(game_storage.load_data(), {})
        self.assertIsNone(game_storage.get_last_player())

    def test_corrupt_save_is_treated_as_empty(self):
        self.save_path.write_text("{broken json", encoding="utf-8")
        self.assertEqual(game_storage.load_data(), {})

    def test_backup_restores_all_profiles_after_reinstall(self):
        profiles = {
            "Ксения": {"emeralds": 120, "game_history": [{"errors": 2}]},
            "Настя": {"emeralds": 300, "task_num": 27},
        }
        game_storage.save_data(profiles)
        game_storage.set_last_player("Настя")
        backup = game_storage.make_backup_bytes()
        self.save_path.unlink()
        self.last_player_path.unlink()

        self.assertEqual(game_storage.restore_backup_bytes(backup), (2, 0))
        self.assertEqual(game_storage.load_data(), profiles)
        self.assertEqual(game_storage.get_last_player(), "Настя")

    def test_restore_does_not_overwrite_existing_player(self):
        game_storage.save_data({"Настя": {"emeralds": 10}})
        backup = game_storage.make_backup_bytes()
        game_storage.save_data({"Настя": {"emeralds": 80}})
        self.assertEqual(game_storage.restore_backup_bytes(backup), (0, 1))
        self.assertEqual(game_storage.load_data()["Настя"]["emeralds"], 80)

    def test_invalid_backup_cannot_change_save(self):
        game_storage.save_data({"Ксения": {"emeralds": 17}})
        for content in (b"not json", b"{}", b'{"format":"mathcraft-backup","version":1,"profiles":{"X":1}}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                game_storage.restore_backup_bytes(content)
        self.assertEqual(game_storage.load_data()["Ксения"]["emeralds"], 17)


if __name__ == "__main__":
    unittest.main()
