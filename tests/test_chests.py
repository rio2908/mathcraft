"""Chest and food persistence checks in a disposable working directory."""

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
class ChestPersistenceTests(unittest.TestCase):
    def test_key_click_grants_reward_once_and_continues_route(self):
        script = """
            import sys
            import threading
            import time
            import pygame
            from game_storage import load_data, save_data

            failure = []

            def play_chest():
                deadline = time.time() + 12
                app = None
                try:
                    while time.time() < deadline:
                        app = sys.modules.get("main")
                        if app and hasattr(app, "chest_answer_buttons") and app.game_state == "REGISTER":
                            break
                        time.sleep(0.02)
                    else:
                        raise AssertionError("Game did not start")

                    p = app.get_player("Тест", remember_player=False)
                    p["task_num"] = 2
                    p["chest_task"] = 2
                    save_data({"Тест": p})
                    app.player_name = "Тест"
                    app.player_data = p
                    app.task_num = 2
                    app.current_world_idx = 0
                    app.step_in_world = 2
                    app.start_chest_encounter()
                    saved = load_data()
                    saved["Тест"]["chest_challenge"]["reward"] = "emeralds"
                    save_data(saved)
                    app.player_data = saved["Тест"]
                    initial = saved["Тест"]["emeralds"]
                    lock = saved["Тест"]["chest_challenge"]
                    correct_index = lock["choices"].index(lock["answer"])
                    time.sleep(0.2)
                    pygame.image.save(app.screen, "chest_screen.png")
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        pos=app.chest_answer_buttons[correct_index].center, button=1
                    ))
                    while time.time() < deadline and not load_data()["Тест"]["chest_challenge"]["finished"]:
                        time.sleep(0.02)
                    assert load_data()["Тест"]["emeralds"] == initial + 10
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        pos=app.chest_answer_buttons[correct_index].center, button=1
                    ))
                    time.sleep(0.1)
                    assert load_data()["Тест"]["emeralds"] == initial + 10
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, pos=app.chest_continue_btn.center, button=1
                    ))
                    while time.time() < deadline and app.game_state != "GAME":
                        time.sleep(0.02)
                    assert app.task_num == 3
                    assert load_data()["Тест"]["chest_challenge"] is None

                    updated = load_data()
                    updated["Тест"]["emeralds"] = 100
                    save_data(updated)
                    app.player_data = updated["Тест"]
                    app.workbench_tab = "POTIONS"
                    app.game_state = "WORKBENCH"
                    apple_button = app.get_shop_row_rects(3, len(app.POTIONS))[2]
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, pos=apple_button.center, button=1
                    ))
                    while time.time() < deadline and load_data()["Тест"]["food_apples"] == 0:
                        time.sleep(0.02)
                    assert load_data()["Тест"]["food_apples"] == 1
                    assert load_data()["Тест"]["emeralds"] == 65

                    updated = load_data()
                    updated["Тест"]["hero_hearts"] = 2
                    save_data(updated)
                    app.player_data = updated["Тест"]
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, pos=app.get_food_use_rect(3).center, button=1
                    ))
                    while time.time() < deadline and load_data()["Тест"]["hero_hearts"] == 2:
                        time.sleep(0.02)
                    assert load_data()["Тест"]["hero_hearts"] == 3
                    assert load_data()["Тест"]["food_apples"] == 0

                except Exception as exc:
                    failure.append(repr(exc))
                finally:
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

            worker = threading.Thread(target=play_chest, daemon=True)
            worker.start()
            import main
            worker.join(timeout=1)
            assert not worker.is_alive()
            assert not failure, failure
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
                [sys.executable, "-c", textwrap.dedent(script)], cwd=temp_dir,
                env=environment, capture_output=True, text=True, timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((Path(temp_dir) / "chest_screen.png").is_file())

    def test_chest_unlock_resume_reward_and_next_marathon(self):
        script = """
            import asyncio
            asyncio.run = lambda coroutine: coroutine.close()
            import main
            from game_storage import load_data, save_data

            p = main.get_player("Ксения", remember_player=False)
            saved = load_data()
            for field in ("clean_biome_streak", "biome_had_error", "chest_task",
                          "chest_challenge", "chest_seen_questions", "hero_hearts",
                          "food_apples", "food_bread"):
                saved["Ксения"].pop(field, None)
            saved["Ксения"]["task_num"] = 5
            saved["Ксения"]["marathon_error_details"] = [{"world": 1, "task": 2}]
            save_data(saved)
            p = main.get_player("Ксения", remember_player=False)
            assert p["clean_biome_streak"] == 0
            assert p["biome_had_error"]
            assert p["hero_hearts"] == 3

            p["task_num"] = 1
            p["clean_biome_streak"] = 0
            p["biome_had_error"] = False
            p["chest_task"] = None
            assert "30 верных ответов на островках" in main.chest_progress_hint(p)
            p["task_num"] = 6
            assert "25 верных ответов на островках" in main.chest_progress_hint(p)
            p["biome_had_error"] = True
            assert "35 верных ответов на островках" in main.chest_progress_hint(p)
            p["chest_task"] = 8
            assert "3 верных ответа на островках" in main.chest_progress_hint(p)

            p["clean_biome_streak"] = 2
            p["biome_had_error"] = False
            main.finish_biome(p, 0)
            assert p["clean_biome_streak"] == 0
            assert 12 <= p["chest_task"] <= 19
            chest_task = p["chest_task"]
            save_data({"Ксения": p})

            main.player_name = "Ксения"
            main.player_data = main.get_player("Ксения", remember_player=False)
            main.task_num = chest_task
            main.game_state = "GAME"
            original_save_data = main.save_data
            def save_before_chest_screen(data):
                assert main.game_state == "GAME"
                original_save_data(data)
            main.save_data = save_before_chest_screen
            main.start_chest_encounter()
            main.save_data = original_save_data
            assert main.game_state == "CHEST_LOCK"
            first_lock = dict(main.player_data["chest_challenge"])
            assert len(main.player_data["chest_seen_questions"]["easy"]) == 1
            main.player_data = main.get_player("Ксения", remember_player=False)
            main.start_chest_encounter()
            assert main.player_data["chest_challenge"] == first_lock
            assert len(main.player_data["chest_seen_questions"]["easy"]) == 1

            p = main.player_data
            wrong_indices = [i for i, value in enumerate(first_lock["choices"])
                             if value != first_lock["answer"]]
            before = p["emeralds"]
            assert main.answer_chest_key(p, wrong_indices[0]) is False
            assert p["chest_challenge"]["tries"] == 1
            assert main.answer_chest_key(p, wrong_indices[0]) is None
            assert main.answer_chest_key(p, wrong_indices[1]) is False
            assert p["chest_challenge"]["finished"]
            assert not p["chest_challenge"]["won"]
            assert p["chest_task"] is None
            assert p["emeralds"] == before
            p["hero_hearts"] = 2
            p["food_apples"] = 1
            assert main.consume_food(p, "apple")
            assert (p["hero_hearts"], p["food_apples"]) == (3, 0)
            assert not main.consume_food(p, "apple")
            p["hero_hearts"] = 2
            p["food_bread"] = 1
            assert main.consume_food(p, "bread")
            assert (p["hero_hearts"], p["food_bread"]) == (3, 0)
            p["hero_hearts"] = 2
            p["totems"] = 1
            assert main.take_battle_hit(p) == "hurt"
            assert (p["hero_hearts"], p["totems"]) == (1, 1)
            assert main.take_battle_hit(p) == "totem"
            assert (p["hero_hearts"], p["totems"]) == (1, 0)
            p["hero_hearts"] = 1
            assert main.take_battle_hit(p) == "down"
            assert p["biome_had_error"]

            p["clean_biome_streak"] = 2
            p["biome_had_error"] = False
            main.finish_biome(p, 4)
            assert p["chest_pending_next_marathon"]
            p["task_num"] = 51
            save_data({"Ксения": p})
            main.player_data = p
            main.reset_entire_marathon()
            updated = load_data()["Ксения"]
            assert 2 <= updated["chest_task"] <= 9
            assert not updated["chest_pending_next_marathon"]
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
                [sys.executable, "-c", textwrap.dedent(script)], cwd=temp_dir,
                env=environment, capture_output=True, text=True, timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
