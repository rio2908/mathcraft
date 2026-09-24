"""Persistence checks for librarian riddles, isolated from real saves."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class LibrarianPersistenceTests(unittest.TestCase):
    def test_question_survives_restart_and_histories_are_per_profile(self):
        script = """
            import asyncio
            asyncio.run = lambda coroutine: coroutine.close()
            import main
            from game_storage import load_data, save_data

            a = main.get_player("Настя", remember_player=False)
            b = main.get_player("Ксения", remember_player=False)
            assert a["sage_seen_questions"] == {"easy": [], "hard": []}
            assert b["sage_seen_questions"] == {"easy": [], "hard": []}

            old_save = load_data()
            del old_save["Настя"]["sage_seen_questions"]
            del old_save["Настя"]["sage_challenge"]
            save_data(old_save)
            a = main.get_player("Настя", remember_player=False)
            assert a["sage_seen_questions"] == {"easy": [], "hard": []}
            assert a["sage_challenge"] is None

            main.player_name = "Настя"
            main.player_data = a
            main.start_sage_encounter()
            first = main.sage_question
            saved = load_data()
            assert saved["Настя"]["sage_seen_questions"]["hard"] == [first]
            assert saved["Ксения"]["sage_seen_questions"]["easy"] == []

            main.player_data = main.get_player("Настя", remember_player=False)
            main.start_sage_encounter()
            assert main.sage_question == first
            assert load_data()["Настя"]["sage_seen_questions"]["hard"] == [first]

            main.reset_entire_marathon()
            assert load_data()["Настя"]["sage_challenge"] is None
            assert load_data()["Настя"]["sage_seen_questions"]["hard"] == [first]
            main.start_sage_encounter()
            assert main.sage_question != first
        """
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-c", textwrap.dedent(script)],
                cwd=temp_dir, env=environment, capture_output=True,
                text=True, timeout=20, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
