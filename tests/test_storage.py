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

    def test_utf8_bom_backup_is_supported(self):
        game_storage.save_data({"Настя": {"emeralds": 42}})
        content = b"\xef\xbb\xbf" + game_storage.make_backup_bytes()
        self.save_path.unlink()
        self.assertEqual(game_storage.restore_backup_bytes(content), (1, 0))
        self.assertEqual(game_storage.load_data()["Настя"]["emeralds"], 42)

    def test_oversized_export_is_rejected_before_creating_unusable_backup(self):
        game_storage.save_data({"Настя": {"emeralds": 42}})
        with patch.object(game_storage, "MAX_BACKUP_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "слишком большой"):
                game_storage.make_backup_bytes()

    def test_failed_restore_write_is_reported_and_existing_progress_is_preserved(self):
        game_storage.save_data({"Новый": {"emeralds": 42}})
        content = game_storage.make_backup_bytes()
        game_storage.save_data({"Настя": {"emeralds": 90}})
        before = self.save_path.read_bytes()
        with patch.object(game_storage.os, "replace", side_effect=OSError("Disk full")):
            with self.assertRaisesRegex(OSError, "Не удалось сохранить"):
                game_storage.restore_backup_bytes(content)
        self.assertEqual(self.save_path.read_bytes(), before)

    def test_manual_emeralds_replace_balance_and_preserve_profiles_and_challenge(self):
        challenge = {"name": "Осень", "active": True, "count": 3, "target_days": 10}
        game_storage.save_data({
            "Настя": {"emeralds": 83, "task_num": 12, "activity_challenge": challenge},
            "Ксения": {"emeralds": 50},
        })
        game_storage.set_last_player("Настя")
        profile = game_storage.set_player_emeralds("Настя", 400)
        self.assertEqual(profile["emeralds"], 400)
        self.assertEqual(profile["task_num"], 12)
        self.assertEqual(profile["activity_challenge"], challenge)
        self.assertEqual(game_storage.load_data()["Настя"], profile)
        self.assertEqual(game_storage.load_data()["Ксения"]["emeralds"], 50)
        self.assertEqual(game_storage.get_last_player(), "Настя")
        self.assertEqual(game_storage.set_player_emeralds("Ксения", 0)["emeralds"], 0)

    def test_invalid_manual_emeralds_and_failed_save_do_not_change_progress(self):
        game_storage.save_data({"Настя": {"emeralds": 83}})
        before = self.save_path.read_bytes()
        for value in (-1, 1.5, "5", True, game_storage.MAX_MANUAL_EMERALDS + 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                game_storage.set_player_emeralds("Настя", value)
        with self.assertRaises(ValueError):
            game_storage.set_player_emeralds("Нет такого игрока", 10)
        with patch.object(game_storage.os, "replace", side_effect=OSError("Disk full")):
            with self.assertRaisesRegex(OSError, "Не удалось сохранить баланс"):
                game_storage.set_player_emeralds("Настя", 400)
        self.assertEqual(self.save_path.read_bytes(), before)

    def test_delete_player_preserves_other_profiles_and_updates_last_player(self):
        kept = {"emeralds": 83, "task_num": 12, "game_history": [{"errors": 2}]}
        game_storage.save_data({"Настя": kept, "Удаляемый": {
            "emeralds": 50, "activity_challenge": {"name": "Осень", "active": True},
        }})
        game_storage.set_last_player("Удаляемый")
        with patch.object(game_storage.challenge_reminders, "sync") as sync:
            self.assertEqual(game_storage.delete_player("Удаляемый"), {"Настя": kept})
            sync.assert_called_once_with({"Настя": kept}, str(self.save_path))
        self.assertEqual(game_storage.load_data(), {"Настя": kept})
        self.assertEqual(game_storage.get_last_player(), "Настя")

    def test_delete_other_player_keeps_selection_and_delete_last_clears_it(self):
        game_storage.save_data({"Настя": {"emeralds": 83}, "Ксения": {"emeralds": 50}})
        game_storage.set_last_player("Настя")
        game_storage.delete_player("Ксения")
        self.assertEqual(game_storage.get_last_player(), "Настя")
        self.assertEqual(game_storage.delete_player("Настя"), {})
        self.assertEqual(game_storage.load_data(), {})
        self.assertIsNone(game_storage.get_last_player())

    def test_failed_or_unknown_deletion_cannot_change_profiles_or_selection(self):
        game_storage.save_data({"Настя": {"emeralds": 83}})
        game_storage.set_last_player("Настя")
        before = self.save_path.read_bytes()
        with self.assertRaises(ValueError):
            game_storage.delete_player("Нет такого игрока")
        with patch.object(game_storage.os, "replace", side_effect=OSError("Disk full")):
            with self.assertRaisesRegex(OSError, "Не удалось удалить"):
                game_storage.delete_player("Настя")
        self.assertEqual(self.save_path.read_bytes(), before)
        self.assertEqual(game_storage.get_last_player(), "Настя")


if __name__ == "__main__":
    unittest.main()
