import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    importlib.util.find_spec("pygame"),
    "pygame is not installed in this environment",
)
class AppSmokeTests(unittest.TestCase):
    def test_app_starts_and_handles_quit_event(self):
        child_code = textwrap.dedent(
            """
            import threading
            import time
            import pygame

            def stop_game():
                deadline = time.time() + 15
                while time.time() < deadline:
                    if pygame.display.get_surface() is not None:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                        return
                    time.sleep(0.02)
                raise RuntimeError("Pygame display did not initialize")

            stopper = threading.Thread(target=stop_game, daemon=True)
            stopper.start()
            import main
            stopper.join(timeout=1)
            if stopper.is_alive():
                raise RuntimeError("Stop thread did not finish")

            profile = main.get_player(
                "Ксения",
                apply_daily_bonus=False,
                remember_player=False,
            )
            for required_field in (
                "disabled_vehicles",
                "disabled_artifacts",
                "luck_potions",
            ):
                if required_field not in profile:
                    raise AssertionError(f"Missing migrated field: {required_field}")

            profile["artifacts"] = ["sharp_sword"]
            if not main.has_active_artifact(profile, "sharp_sword"):
                raise AssertionError("Owned artifact should be active by default")
            profile["disabled_artifacts"] = ["sharp_sword"]
            if main.has_active_artifact(profile, "sharp_sword"):
                raise AssertionError("Disabled artifact must not affect combat")

            sprite_surface = pygame.Surface((120, 120))
            sprite_surface.fill((35, 45, 55))
            main.draw_mob(sprite_surface, 60, 60, "creeper")
            if sprite_surface.get_at((90, 60))[:3] != (35, 45, 55):
                raise AssertionError("Mob drawing must not add a glowing backdrop")

            main.game_state = "FINAL_STATS"
            main.login_show_all_players = False
            main.login_page = 2
            main.finish_marathon_to_menu()
            assert main.game_state == "LOGIN"
            assert main.login_show_all_players
            assert main.login_page == 0
            """
        )
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        })

        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-c", child_code],
                cwd=temp_dir,
                env=environment,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def test_finish_buttons_open_player_selection(self):
        child_code = textwrap.dedent("""
            import sys
            import pygame

            original_flip = pygame.display.flip
            frame = 0
            def click(rect):
                pygame.event.post(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center
                ))
            def flip():
                global frame
                original_flip()
                frame += 1
                app = sys.modules["main"]
                if frame == 1:
                    app.player_name = "Kid"
                    app.player_data = app.get_player("Kid", remember_player=False)
                    app.boss_won = True
                    app.game_state = "BOSS_BATTLE"
                elif frame == 2:
                    click(app.boss_btn_finish)
                elif frame == 3:
                    assert app.game_state == "LOGIN"
                    assert app.login_show_all_players
                    app.game_state = "FINAL_STATS"
                    click(app.stats_finish_btn)
                elif frame == 4:
                    assert app.game_state == "LOGIN"
                    assert app.login_show_all_players
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            pygame.display.flip = flip
            import main
        """)
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-c", child_code], cwd=temp_dir,
                env=environment, capture_output=True, text=True,
                timeout=20, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
