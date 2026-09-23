import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class RegistrationTests(unittest.TestCase):
    def run_game(self, script, workdir):
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        })
        result = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(script)],
            cwd=workdir,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_avatar_profile_and_show_it_on_next_start(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_game("""
                import sys
                import threading
                import time
                import pygame

                def register():
                    deadline = time.time() + 12
                    while time.time() < deadline:
                        app = sys.modules.get("main")
                        if app and hasattr(app, "register_submit_rect") and app.game_state == "REGISTER":
                            pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text="Alex"))
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.register_boy_rect.center, button=1))
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.register_hard_rect.center, button=1))
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.register_submit_rect.center, button=1))
                            break
                        time.sleep(0.02)
                    else:
                        raise RuntimeError("Registration screen did not open")
                    while time.time() < deadline:
                        if app.game_state == "GAME":
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                            return
                        time.sleep(0.02)
                    raise RuntimeError("Registration did not start the game")

                worker = threading.Thread(target=register, daemon=True)
                worker.start()
                import main
                worker.join(timeout=1)
                if worker.is_alive():
                    raise RuntimeError("Registration worker did not finish")
            """, temp_dir)

            profiles = json.loads((Path(temp_dir) / "mc_math_save.json").read_text(encoding="utf-8"))
            self.assertEqual(list(profiles), ["Alex"])
            self.assertEqual(profiles["Alex"]["avatar"], "boy")
            self.assertEqual(profiles["Alex"]["difficulty"], "hard")
            self.assertEqual((Path(temp_dir) / "mc_last_player.txt").read_text(encoding="utf-8"), "Alex")

            self.run_game("""
                import sys
                import threading
                import time
                import pygame

                def check_login():
                    deadline = time.time() + 12
                    while time.time() < deadline:
                        app = sys.modules.get("main")
                        if app and hasattr(app, "get_login_profiles") and app.game_state == "LOGIN":
                            if app.get_login_profiles() != ["Alex"]:
                                raise AssertionError("Last profile is not selected")
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                            return
                        time.sleep(0.02)
                    raise RuntimeError("Saved profile login did not open")

                worker = threading.Thread(target=check_login, daemon=True)
                worker.start()
                import main
                worker.join(timeout=1)
                if worker.is_alive():
                    raise RuntimeError("Login worker did not finish")
            """, temp_dir)

    def test_existing_nastya_profile_keeps_its_progress_and_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "mc_math_save.json"
            save_path.write_text(json.dumps({
                "Настя": {
                    "emeralds": 83,
                    "task_num": 12,
                }
            }, ensure_ascii=False), encoding="utf-8")
            self.run_game("""
                import sys
                import threading
                import time
                import pygame

                def stop():
                    deadline = time.time() + 12
                    while time.time() < deadline:
                        app = sys.modules.get("main")
                        if app and hasattr(app, "get_login_profiles") and app.game_state == "LOGIN":
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                            return
                        time.sleep(0.02)
                    raise RuntimeError("Existing profile did not open")

                worker = threading.Thread(target=stop, daemon=True)
                worker.start()
                import main
                worker.join(timeout=1)
            """, temp_dir)
            profile = json.loads(save_path.read_text(encoding="utf-8"))["Настя"]
            self.assertEqual(profile["emeralds"], 83)
            self.assertEqual(profile["task_num"], 12)
            self.assertEqual(profile["difficulty"], "hard")
            self.assertEqual(profile["avatar"], "girl")

    def test_switching_existing_players_remembers_new_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "mc_math_save.json").write_text(
                json.dumps({"Alex": {"emeralds": 25}, "Nina": {"emeralds": 41}}),
                encoding="utf-8",
            )
            (Path(temp_dir) / "mc_last_player.txt").write_text("Alex", encoding="utf-8")
            self.run_game("""
                import sys
                import threading
                import time
                import pygame

                def switch_player():
                    deadline = time.time() + 12
                    while time.time() < deadline:
                        app = sys.modules.get("main")
                        if app and hasattr(app, "change_player_btn") and app.game_state == "LOGIN":
                            if app.get_login_profiles() != ["Alex"]:
                                raise AssertionError("Wrong startup profile")
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.change_player_btn.center, button=1))
                            break
                        time.sleep(0.02)
                    while time.time() < deadline:
                        if app.get_login_profiles() == ["Alex", "Nina"] and "Nina" in app.player_play_buttons:
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=app.player_play_buttons["Nina"].center, button=1))
                            break
                        time.sleep(0.02)
                    while time.time() < deadline:
                        if app.game_state == "GAME" and app.player_name == "Nina":
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                            return
                        time.sleep(0.02)
                    raise RuntimeError("Player switch did not finish")

                worker = threading.Thread(target=switch_player, daemon=True)
                worker.start()
                import main
                worker.join(timeout=1)
                if worker.is_alive():
                    raise RuntimeError("Switch worker did not finish")
            """, temp_dir)
            self.assertEqual((Path(temp_dir) / "mc_last_player.txt").read_text(encoding="utf-8"), "Nina")
            profiles = json.loads((Path(temp_dir) / "mc_math_save.json").read_text(encoding="utf-8"))
            self.assertEqual(profiles["Alex"]["emeralds"], 25)
            self.assertEqual(profiles["Nina"]["emeralds"], 41)


if __name__ == "__main__":
    unittest.main()
