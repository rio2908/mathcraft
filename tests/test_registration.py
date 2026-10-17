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

    def test_backup_screen_opens_before_any_player_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_game("""
                import sys
                import threading
                import time
                import pygame

                def check_backup():
                    deadline = time.time() + 12
                    while time.time() < deadline:
                        app = sys.modules.get("main")
                        if app and hasattr(app, "backup_entry_btn") and app.game_state == "REGISTER":
                            pygame.event.post(pygame.event.Event(
                                pygame.MOUSEBUTTONDOWN, pos=app.backup_entry_btn.center, button=1))
                            break
                        time.sleep(0.02)
                    else:
                        raise RuntimeError("Registration screen did not open")
                    while time.time() < deadline:
                        if app.game_state == "BACKUP":
                            pygame.event.post(pygame.event.Event(
                                pygame.MOUSEBUTTONDOWN, pos=app.backup_back_btn.center, button=1))
                            break
                        time.sleep(0.02)
                    else:
                        raise RuntimeError("Backup screen did not open")
                    while time.time() < deadline:
                        if app.game_state == "REGISTER":
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                            return
                        time.sleep(0.02)
                    raise RuntimeError("Backup screen did not close")

                worker = threading.Thread(target=check_backup, daemon=True)
                worker.start()
                import main
                worker.join(timeout=1)
                if worker.is_alive():
                    raise RuntimeError("Backup worker did not finish")
            """, temp_dir)

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

    def test_first_players_click_after_registration_does_not_crash_and_can_resume(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_game("""
                import sys
                import pygame
                frames = 0
                labels = {}
                original_draw = None

                def click(rect):
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                        button=1, pos=rect.center))

                def capture_button(surface, rect, text, *args, **kwargs):
                    app = sys.modules['main']
                    if app.game_state == 'LOGIN':
                        for name, button in app.player_play_buttons.items():
                            if rect == button:
                                labels[name] = text
                    return original_draw(surface, rect, text, *args, **kwargs)

                def flip():
                    global frames, original_draw
                    frames += 1
                    app = sys.modules['main']
                    if frames == 1:
                        app.audio_attempted = True
                        original_draw = app.draw_mc_button
                        app.draw_mc_button = capture_button
                        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text='Alex'))
                        click(app.register_submit_rect)
                    elif frames == 2:
                        assert app.game_state == 'GAME'
                        assert not app.player_play_buttons, 'The first menu must not rely on cached buttons'
                        click(app.nav_players)
                    elif frames == 3:
                        assert app.game_state == 'LOGIN'
                        assert set(app.player_play_buttons) == {'Alex'}
                        assert labels['Alex'] == 'Продолжить', labels
                        assert app.load_data()['Alex']['marathon_started'] is True
                        assert app.load_data()['Alex']['task_num'] == 1
                        click(app.player_play_buttons['Alex'])
                    elif frames == 4:
                        assert app.game_state == 'GAME'
                        assert app.task_num == 1
                        click(app.nav_players)
                    elif frames == 5:
                        assert app.game_state == 'LOGIN'
                        assert labels['Alex'] == 'Продолжить'
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_player_labels_follow_each_profile_progress_and_pagination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "mc_math_save.json").write_text(json.dumps({
                "New": {"task_num": 1},
                "Active": {"task_num": 12},
                "First": {"task_num": 1, "marathon_started": True},
                "Legacy": {"task_num": 1, "marathon_elapsed_seconds": 20},
                "Done": {"task_num": 51},
            }), encoding="utf-8")
            (Path(temp_dir) / "mc_last_player.txt").write_text("Active", encoding="utf-8")
            self.run_game("""
                import os
                import sys
                import pygame
                labels = {}
                frames = 0

                def click(rect):
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                        button=1, pos=rect.center))

                def capture_button(surface, rect, text, *args, **kwargs):
                    app = sys.modules['main']
                    if app.game_state == 'LOGIN':
                        for name, button in app.player_play_buttons.items():
                            if rect == button:
                                labels[name] = text
                    return original_draw(surface, rect, text, *args, **kwargs)

                def flip():
                    global frames
                    frames += 1
                    app = sys.modules['main']
                    if frames == 1:
                        assert labels == {'Active': 'Продолжить'}, labels
                        click(app.change_player_btn)
                    elif frames == 2:
                        assert set(app.player_play_buttons) == {'New', 'Active', 'First'}
                        assert labels['New'] == 'Играть', labels
                        assert labels['Active'] == labels['First'] == 'Продолжить', labels
                        folder = os.environ.get('MC_TEST_SCREENSHOTS')
                        if folder:
                            pygame.image.save(app.screen, os.path.join(folder, 'players-progress.png'))
                        click(app.login_next_btn)
                    elif frames == 3:
                        assert set(app.player_play_buttons) == {'Legacy', 'Done'}
                        assert labels['Legacy'] == 'Продолжить', labels
                        assert labels['Done'] == 'Итоги', labels
                        click(app.login_prev_btn)
                    elif frames == 4:
                        assert set(app.player_play_buttons) == {'New', 'Active', 'First'}
                        click(app.player_play_buttons['New'])
                    elif frames == 5:
                        assert app.game_state == 'GAME' and app.player_name == 'New'
                        click(app.nav_players)
                    elif frames == 6:
                        assert labels['New'] == 'Продолжить', labels
                        assert app.load_data()['New']['marathon_started'] is True
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                # Install the draw observer before the first LOGIN render.
                import asyncio
                run = asyncio.run
                asyncio.run = lambda coroutine: coroutine.close()
                import main
                asyncio.run = run
                original_draw = main.draw_mc_button
                main.draw_mc_button = capture_button
                main.audio_attempted = True
                pygame.display.flip = flip
                run(main.main())
            """, temp_dir)

    def test_started_flag_migrates_existing_profiles_without_changing_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mc_math_save.json"
            original = {
                "Fresh": {"task_num": 1, "emeralds": 20},
                "Timed": {"task_num": 1, "marathon_elapsed_seconds": 20, "emeralds": 30},
                "Errors": {"task_num": 1, "marathon_errors": 1, "emeralds": 40},
                "Настя": {"task_num": 12, "emeralds": 83},
                "Done": {"task_num": 51, "emeralds": 90},
            }
            path.write_text(json.dumps(original), encoding="utf-8")
            self.run_game("""
                import asyncio
                import pygame
                asyncio.run = lambda coroutine: coroutine.close()
                import main
                for _ in range(2):
                    for name, started in (('Fresh', False), ('Timed', True), ('Errors', True),
                                          ('Настя', True), ('Done', False)):
                        profile = main.get_player(name, False, False)
                        assert profile['marathon_started'] is started, name
                    assert main.get_player('Настя', False, False)['difficulty'] == 'hard'
                pygame.quit()
            """, temp_dir)
            saved = json.loads(path.read_text(encoding="utf-8"))
            for name, profile in original.items():
                for field, value in profile.items():
                    self.assertEqual(saved[name][field], value)

    def test_queued_play_and_players_clicks_use_current_layout_and_saved_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "mc_math_save.json").write_text(json.dumps({
                "First": {"task_num": 1}, "Second": {"task_num": 12, "sage_task": None},
            }), encoding="utf-8")
            (Path(temp_dir) / "mc_last_player.txt").write_text("First", encoding="utf-8")
            self.run_game("""
                import asyncio
                import pygame
                run = asyncio.run
                asyncio.run = lambda coroutine: coroutine.close()
                import main as app
                asyncio.run = run
                app.audio_attempted = True
                labels = {}
                original_draw = app.draw_mc_button
                def draw(surface, rect, text, *args, **kwargs):
                    if app.game_state == 'LOGIN':
                        for name, button in app.player_play_buttons.items():
                            if rect == button:
                                labels[name] = text
                    return original_draw(surface, rect, text, *args, **kwargs)
                app.draw_mc_button = draw
                frames = 0
                def click(rect):
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                        button=1, pos=rect.center))
                def flip():
                    global frames
                    frames += 1
                    if frames == 1:
                        assert labels['First'] == 'Играть'
                        click(app.player_play_buttons['First'])
                        click(app.nav_players)  # Both events in one frame.
                    else:
                        assert app.game_state == 'LOGIN'
                        assert set(app.player_play_buttons) == {'First', 'Second'}
                        assert labels['First'] == labels['Second'] == 'Продолжить', labels
                        if frames >= 20:
                            pygame.event.post(pygame.event.Event(pygame.QUIT))
                        else:
                            name = 'First' if frames % 2 else 'Second'
                            click(app.player_play_buttons[name])
                            click(app.nav_players)
                pygame.display.flip = flip
                run(app.main())
            """, temp_dir)


if __name__ == "__main__":
    unittest.main()
