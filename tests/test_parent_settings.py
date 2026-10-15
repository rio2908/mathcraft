import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class ParentSettingsUITests(unittest.TestCase):
    def test_pin_balance_apply_validation_player_switch_and_game_balance(self):
        with tempfile.TemporaryDirectory() as directory:
            save = Path(directory) / "mc_math_save.json"
            challenge = {"name": "Осень", "target_days": 10, "count": 3, "active": True, "last_date": "2026-10-01"}
            save.write_text(json.dumps({
                "Настя": {"emeralds": 83, "task_num": 12, "activity_challenge": challenge},
                "Ксения": {"emeralds": 50},
            }), encoding="utf-8")
            (Path(directory) / "mc_last_player.txt").write_text("Настя", encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
                "PYGAME_HIDE_SUPPORT_PROMPT": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            })
            script = textwrap.dedent('''
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
                                    time.sleep(0.05)
                                    return
                                time.sleep(0.01)
                            raise AssertionError("Timed out waiting for parent settings")
                        wait(lambda: hasattr(sys.modules.get("main"), "parent_emeralds_apply_btn"))
                        app = sys.modules["main"]
                        def click(rect):
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1))
                        def state(value):
                            wait(lambda: app.game_state == value)
                        def type_balance(value):
                            click(app.parent_emeralds_rect)
                            for _ in range(10):
                                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
                            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=value))
                        def snapshot(name):
                            folder = os.environ.get("MC_TEST_SCREENSHOTS")
                            if folder:
                                tick = app.anim_tick
                                wait(lambda: app.anim_tick >= tick + 3)
                                pygame.image.save(app.screen, os.path.join(folder, name + ".png"))
                        state("LOGIN")
                        click(app.parent_lock_btn)
                        state("PARENT_PIN")
                        for digit in "2908":
                            click(app.pin_buttons[digit])
                        click(app.pin_buttons["OK"])
                        state("PARENT_MENU")
                        snapshot("parent-menu")
                        click(app.parent_emeralds_btn)
                        state("EMERALD_SETTINGS")
                        original_challenge = dict(app.load_data()["Настя"]["activity_challenge"])
                        type_balance("400")
                        time.sleep(0.15)
                        assert app.load_data()["Настя"]["emeralds"] == 83, "Typing alone must not apply changes"
                        click(app.parent_emeralds_apply_btn)
                        wait(lambda: app.load_data()["Настя"]["emeralds"] == 400)
                        assert app.player_data["emeralds"] == 400
                        assert app.load_data()["Настя"]["activity_challenge"] == original_challenge
                        snapshot("parent-emeralds")
                        for invalid in ("-5", "1.5", "abc", "", "10000000"):
                            type_balance(invalid)
                            click(app.parent_emeralds_apply_btn)
                            time.sleep(0.12)
                            assert app.load_data()["Настя"]["emeralds"] == 400, invalid
                        click(app.challenge_next_player_btn)
                        time.sleep(0.15)
                        type_balance("0")
                        click(app.parent_emeralds_apply_btn)
                        wait(lambda: app.load_data()["Ксения"]["emeralds"] == 0)
                        assert app.load_data()["Настя"]["emeralds"] == 400
                        assert app.player_data["emeralds"] == 400, "Editing another player must not change active player"
                        click(app.parent_back_btn)
                        state("PARENT_MENU")
                        click(app.parent_back_btn)
                        state("LOGIN")
                        app.enter_player("Настя")
                        wait(lambda: app.player_data.get("emeralds") == 400)
                        assert app.task_num == 12
                        assert app.player_data["activity_challenge"] == original_challenge
                        snapshot("parent-emeralds-game")
                    except BaseException as error:
                        errors.append(error)
                    finally:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                worker = threading.Thread(target=check, daemon=True)
                worker.start()
                import main
                worker.join(2)
                assert not worker.is_alive()
                if errors:
                    raise errors[0]
            ''')
            result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=environment,
                                    capture_output=True, text=True, timeout=40, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            profiles = json.loads(save.read_text(encoding="utf-8"))
            self.assertEqual(profiles["Настя"]["emeralds"], 400)
            self.assertEqual(profiles["Ксения"]["emeralds"], 0)
            self.assertEqual(profiles["Настя"]["activity_challenge"], challenge)
