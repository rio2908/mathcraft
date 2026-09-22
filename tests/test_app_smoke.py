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


if __name__ == "__main__":
    unittest.main()
