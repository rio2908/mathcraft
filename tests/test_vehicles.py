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
class VehicleShopTests(unittest.TestCase):
    def test_purchased_pig_is_previewed_immediately_and_used_on_the_route(self):
        child_code = textwrap.dedent("""
            import sys
            import pygame

            original_flip = pygame.display.flip
            frame = 0
            drawn_vehicles = []

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
                    player = app.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                    player["emeralds"] = 100
                    app.save_data({"Kid": player})
                    app.player_data = player
                    app.current_world_idx = 0
                    app.workbench_tab = "VEHICLES"
                    app.game_state = "WORKBENCH"
                    original_draw = app.draw_steve_animated
                    def record_draw(*args, **kwargs):
                        drawn_vehicles.append((app.game_state, args[3]))
                        return original_draw(*args, **kwargs)
                    app.draw_steve_animated = record_draw
                elif frame == 2:
                    assert drawn_vehicles[-1] == ("WORKBENCH", "foot")
                    click(app.get_shop_row_rects(0, len(app.WORLDS))[2])
                elif frame == 3:
                    player = app.load_data()["Kid"]
                    assert "pig" in player["owned_vehicles"]
                    assert player["emeralds"] == 60
                    assert drawn_vehicles[-1] == ("WORKBENCH", "pig")
                    click(pygame.Rect(30, 12, 100, 32))
                elif frame == 4:
                    assert app.game_state == "GAME"
                    assert drawn_vehicles[-1] == ("GAME", "pig")
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
                [sys.executable, "-c", child_code],
                cwd=temp_dir,
                env=environment,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            saved = json.loads((Path(temp_dir) / "mc_math_save.json").read_text(encoding="utf-8"))
            self.assertIn("pig", saved["Kid"]["owned_vehicles"])


if __name__ == "__main__":
    unittest.main()
