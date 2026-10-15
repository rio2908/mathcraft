import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from game_tasks import credit_activity_day, new_activity_challenge, start_activity_challenge


class ActivityChallengeTests(unittest.TestCase):
    def test_unique_days_completion_and_explicit_restart(self):
        profile = {"activity_challenge": new_activity_challenge()}
        self.assertIsNone(credit_activity_day(profile, "2026-10-01"))
        start_activity_challenge(profile, "  Осенний   марафон  ", 2)
        first = credit_activity_day(profile, "2026-10-01")
        self.assertEqual((first["count"], first["remaining"]), (1, 1))
        # A save/reload and another victory today do not grant a second day.
        profile = json.loads(json.dumps(profile))
        duplicate = credit_activity_day(profile, "2026-10-01")
        self.assertFalse(duplicate["credited"])
        self.assertEqual(duplicate["count"], 1)
        with self.assertRaises(ValueError):
            start_activity_challenge(profile, "Замена", 1)
        final = credit_activity_day(profile, "2026-10-05")
        self.assertEqual(final["name"], "Осенний марафон")
        self.assertTrue(final["completed"])
        self.assertEqual((final["count"], final["remaining"]), (2, 0))
        self.assertFalse(profile["activity_challenge"]["active"])
        self.assertEqual(profile["activity_challenge"]["count"], 0)
        self.assertIsNone(credit_activity_day(profile, "2026-10-06"))
        start_activity_challenge(profile, "Новый", 1)
        self.assertFalse(credit_activity_day(profile, "2026-10-05")["credited"])
        self.assertTrue(credit_activity_day(profile, "2026-10-06")["completed"])

    def test_validation_and_profile_isolation(self):
        first, second = {}, {}
        for name, days in (("", 1), (" " * 3, 5), ("x" * 33, 1), ("Test", 0), ("Test", 366)):
            with self.assertRaises(ValueError):
                start_activity_challenge(first, name, days)
        start_activity_challenge(first, "Первый", 365)
        start_activity_challenge(second, "Второй", 1)
        credit_activity_day(first, "2026-10-01")
        self.assertEqual(second["activity_challenge"]["count"], 0)


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class ActivityChallengeUITests(unittest.TestCase):
    def test_pin_settings_victory_migration_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mc_math_save.json"
            path.write_text(json.dumps({"Настя": {"emeralds": 83, "task_num": 12}, "Ксения": {}}), encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
                "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            })
            result = subprocess.run([sys.executable, "-c", textwrap.dedent('''
                import os
                import sys
                import threading
                import time
                import pygame

                errors = []
                def check():
                    try:
                        deadline = time.time() + 25
                        def wait(predicate):
                            while time.time() < deadline:
                                if predicate():
                                    time.sleep(0.08)
                                    return
                                time.sleep(0.01)
                            raise AssertionError("Timed out waiting for UI")
                        wait(lambda: hasattr(sys.modules.get("main"), "challenge_start_btn"))
                        app = sys.modules["main"]
                        def click(rect):
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1))
                        def state(value):
                            wait(lambda: app.game_state == value)
                        def snapshot(name):
                            folder = os.environ.get("MC_TEST_SCREENSHOTS")
                            if folder:
                                tick = app.anim_tick
                                wait(lambda: app.anim_tick >= tick + 3)
                                pygame.image.save(app.screen, os.path.join(folder, name + ".png"))
                        state("LOGIN")
                        snapshot("challenge-login")
                        click(app.parent_lock_btn)
                        state("PARENT_PIN")
                        for key in "0000":
                            click(app.pin_buttons[key])
                        click(app.pin_buttons["OK"])
                        time.sleep(0.15)
                        assert app.game_state == "PARENT_PIN"
                        snapshot("challenge-pin")
                        for key in "2908":
                            click(app.pin_buttons[key])
                        click(app.pin_buttons["OK"])
                        state("PARENT_MENU")
                        snapshot("challenge-secret-menu")
                        click(app.parent_settings_btn)
                        state("CHALLENGE_SETTINGS")
                        click(app.challenge_name_rect)
                        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text="Осенний марафон"))
                        click(app.challenge_days_rect)
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
                        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text="1"))
                        click(app.challenge_start_btn)
                        wait(lambda: app.load_data()["Настя"]["activity_challenge"]["active"])
                        snapshot("challenge-settings")
                        p = app.load_data()["Настя"]
                        assert p["task_num"] == 12 and p["difficulty"] == "hard" and p["emeralds"] == 83
                        assert p["activity_challenge"]["target_days"] == 1
                        assert app.get_player("Ксения", False, False)["activity_challenge"]["active"] is False
                        # Leaving settings locks access again.
                        click(app.parent_back_btn)
                        state("PARENT_MENU")
                        click(app.parent_back_btn)
                        state("LOGIN")
                        click(app.parent_lock_btn)
                        state("PARENT_PIN")
                        click(app.parent_back_btn)
                        state("LOGIN")
                        app.enter_player("Настя")
                        app.reset_entire_marathon()
                        assert app.load_data()["Настя"]["activity_challenge"]["active"]
                        # Exercise the real final-answer handler, not just the pure counter.
                        app.current_world_idx = 4
                        app.task_num = 50
                        app.start_boss_battle()
                        app.boss_streak = app.boss_max_hp - 1
                        correct_index = app.boss_choices.index(app.boss_ans)
                        click(app.boss_answer_buttons[correct_index])
                        wait(lambda: app.boss_won)
                        snapshot("challenge-victory")
                        p = app.load_data()["Настя"]
                        assert p["activity_challenge"]["count"] == 0
                        assert p["activity_challenge"]["active"] is False
                        assert p["game_history"][-1]["activity_challenge"]["completed"]
                        click(app.boss_btn_stats)
                        state("FINAL_STATS")
                        snapshot("challenge-final-stats")
                        app.enter_player("Настя")
                        state("GAME")
                        snapshot("challenge-restored-result")
                        # A completed marathon is not credited again on reload.
                        assert len(app.load_data()["Настя"]["game_history"]) == 1
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                worker = threading.Thread(target=check, daemon=True)
                worker.start()
                import main
                worker.join(timeout=2)
                assert not worker.is_alive()
                if errors:
                    raise errors[0]
            ''')], cwd=directory, env=environment, capture_output=True, text=True, timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(saved["Настя"]["activity_challenge"]["active"])
            self.assertEqual(saved["Настя"]["game_history"][-1]["activity_challenge"]["remaining"], 0)
