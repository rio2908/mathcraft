"""Witch curse and cave-spider web behavior in isolated save directories."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from game_content import MOB_ABILITIES


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MobAbilityBalanceTests(unittest.TestCase):
    def test_cave_spider_web_chance_and_duration(self):
        self.assertEqual(MOB_ABILITIES["cave_spider"]["web_chance"], 0.9)
        self.assertEqual(MOB_ABILITIES["cave_spider"]["web_seconds"], 10.0)


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class MobEffectTests(unittest.TestCase):
    def run_app(self, script, workdir):
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy",
            "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        })
        result = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(script)], cwd=workdir,
            env=environment, capture_output=True, text=True, timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_nether_mob_uses_two_operation_tasks_that_fit_battle_box(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main

                for difficulty in ("easy", "hard"):
                    player = main.get_player("Тест", remember_player=False, difficulty=difficulty)
                    player["difficulty"] = difficulty
                    main.player_name = "Тест"
                    main.task_num = 35
                    for mob_id in ("blaze", "magma_cube", "piglin", "vampire"):
                        player["marathon_route"][3]["mob_id"] = mob_id
                        for _ in range(100):
                            task = main.make_mob_battle_task(player, 3)
                            assert task[3] == "mixed", (mob_id, difficulty, task)
                            assert len(task[4].split()) == 5, task
                            assert main.FONT_TITLE.size(task[0])[0] <= 260, task
            """, temp_dir)

    def test_magma_answers_rotate_then_click_uses_visible_position(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, threading, time, traceback, pygame
                from game_storage import save_data
                failure = []

                def play():
                    try:
                        deadline = time.time() + 10
                        while time.time() < deadline:
                            app = sys.modules.get("main")
                            if app and hasattr(app, "mob_answer_buttons") and app.game_state == "REGISTER":
                                break
                            time.sleep(.02)
                        else:
                            raise AssertionError("Game did not start")
                        player = app.get_player("Тест", remember_player=False)
                        player["marathon_route"][3]["mob_id"] = "magma_cube"
                        player["marathon_route"][3]["mob_name"] = "Магмовый куб"
                        player["task_num"] = 35
                        save_data({"Тест": player})
                        app.player_name = "Тест"
                        app.player_data = player
                        app.task_num = 35
                        app.current_world_idx = 3
                        app.step_in_world = 5
                        app.start_mob_encounter()
                        original = list(app.mob_choices)
                        hidden = next(i for i, answer in enumerate(original) if answer != app.mob_ans)
                        app.mob_hint_hidden = hidden
                        app.mob_swap_seconds_left = .01
                        while time.time() < deadline and app.mob_choices == original:
                            time.sleep(.02)
                        assert app.mob_choices != original
                        assert app.mob_choices[hidden] == original[hidden]
                        assert app.mob_swap_seconds_left > 2.0
                        time.sleep(.05)
                        hp_before = app.mob_hp
                        correct = app.mob_choices.index(app.mob_ans)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, pos=app.mob_answer_buttons[correct].center, button=1))
                        while time.time() < deadline and app.mob_hp == hp_before:
                            time.sleep(.02)
                        assert app.mob_hp < hp_before
                        assert app.mob_swap_seconds_left > 2.0
                    except Exception:
                        failure.append(traceback.format_exc())
                    finally:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                worker = threading.Thread(target=play, daemon=True)
                worker.start()
                import main
                worker.join(timeout=3)
                assert not worker.is_alive()
                assert not failure, failure
            """, temp_dir)

    def test_frog_wand_removes_magma_ability_and_replaces_question(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, pygame
                original_flip = pygame.display.flip
                frames = 0
                transformed_choices = None

                def flip():
                    global frames, transformed_choices
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        player = app.get_player("Тест", remember_player=False)
                        player["artifacts"] = ["frog_wand"]
                        player["artifact_charges"] = {"frog_wand": 1}
                        player["marathon_route"][3]["mob_id"] = "magma_cube"
                        player["marathon_route"][3]["mob_name"] = "Магмовый куб"
                        player["marathon_route"][3]["ops"] = ["+"]
                        player["task_num"] = 35
                        app.save_data({"Тест": player})
                        app.player_name = "Тест"
                        app.player_data = player
                        app.task_num = 35
                        app.current_world_idx = 3
                        app.step_in_world = 5
                        app.start_mob_encounter()
                        assert app.mob_op == "mixed"
                        app.mob_hint_hidden = next(
                            i for i, answer in enumerate(app.mob_choices) if answer != app.mob_ans
                        )
                    elif frames == 2:
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=app.mob_frog_btn.center
                        ))
                    elif frames == 3:
                        assert app.mob_hp == app.mob_max_hp == 1
                        assert app.mob_op == "+"
                        assert app.mob_hint_hidden == -1
                        assert app.mob_swap_seconds_left == 0
                        assert app.load_data()["Тест"]["frog_mob_task"] == 35
                        transformed_choices = list(app.mob_choices)
                    elif frames == 4:
                        assert app.mob_choices == transformed_choices
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_resumed_frog_ignores_stale_web_and_heat_effects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main

                player = main.get_player("Тест", remember_player=False)
                player["marathon_route"][1]["mob_id"] = "cave_spider"
                player["marathon_route"][1]["ops"] = ["+"]
                player["task_num"] = 15
                player["frog_mob_task"] = 15
                player["web_seconds_left"] = 4.5
                player["heat_rune_task"] = 15
                player["heat_rune_seconds_left"] = 6.0
                main.save_data({"Тест": player})
                main.player_name = "Тест"
                main.player_data = player
                main.task_num = 15
                main.current_world_idx = 1
                main.start_mob_encounter()
                saved = main.load_data()["Тест"]
                assert main.mob_hp == main.mob_max_hp == 1
                assert main.mob_web_seconds_left == 0
                assert main.mob_heat_seconds_left == 0
                assert main.mob_op == "+"
                assert saved["web_seconds_left"] == 0
                assert saved["heat_rune_task"] is None
                assert saved["heat_rune_seconds_left"] == 0
            """, temp_dir)

    def test_curse_persists_disables_equipment_and_resets_next_marathon(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main
                from game_storage import load_data, save_data

                p = main.get_player("Тест", remember_player=False)
                p["marathon_route"][2]["mob_id"] = "witch"
                p["marathon_route"][2]["ops"] = ["*"]
                assert all(main.make_mob_battle_task(p, 2)[3] == "*" for _ in range(5))
                p["helmet"] = "iron"
                p["helmet_durability"] = {"iron": 6}
                p["artifacts"] = ["sharp_sword"]
                p["artifact_charges"] = {"sharp_sword": 3}
                p["food_apples"] = 1
                p["totems"] = 2
                assert main.apply_witch_curse(p)
                assert not main.apply_witch_curse(p)
                assert p["hero_hearts"] == 1
                assert main.hero_max_hearts(p) == 1
                assert main.use_helmet_protection(p) is None
                assert not main.has_active_artifact(p, "sharp_sword")
                assert not main.consume_food(p, "apple")
                assert main.take_battle_hit(p) == "down"
                assert p["totems"] == 2
                save_data({"Тест": p})

                reloaded = main.get_player("Тест", remember_player=False)
                assert reloaded["hero_frog"]
                assert reloaded["hero_hearts"] == 0
                main.player_name = "Тест"
                main.player_data = reloaded
                main.reset_entire_marathon()
                reset = load_data()["Тест"]
                assert not reset["hero_frog"]
                assert reset["hero_hearts"] == 3
                assert reset["artifacts"] == ["sharp_sword"]
                assert reset["totems"] == 2
            """, temp_dir)

    def test_witch_wrong_answer_transforms_without_immediate_defeat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, threading, time, pygame
                from game_storage import load_data, save_data
                failure = []

                def play():
                    try:
                        deadline = time.time() + 12
                        while time.time() < deadline:
                            app = sys.modules.get("main")
                            if app and hasattr(app, "mob_answer_buttons") and app.game_state == "REGISTER":
                                break
                            time.sleep(.02)
                        else:
                            raise AssertionError("Game did not start")
                        p = app.get_player("Тест", remember_player=False)
                        p["marathon_route"][2]["mob_id"] = "witch"
                        p["marathon_route"][2]["mob_name"] = "Ведьма"
                        p["task_num"] = 25
                        save_data({"Тест": p})
                        app.player_name = "Тест"
                        app.player_data = p
                        app.task_num = 25
                        app.current_world_idx = 2
                        app.step_in_world = 5
                        app.start_mob_encounter()
                        wrong = next(i for i, answer in enumerate(app.mob_choices) if answer != app.mob_ans)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, pos=app.mob_answer_buttons[wrong].center, button=1))
                        while time.time() < deadline and not load_data()["Тест"]["hero_frog"]:
                            time.sleep(.02)
                        assert load_data()["Тест"]["hero_frog"]
                        assert app.game_state == "MOB_BATTLE"
                        assert app.player_data["hero_hearts"] == 1
                        assert not app.mob_failed_reset
                    except Exception as error:
                        failure.append(repr(error))
                    finally:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                worker = threading.Thread(target=play, daemon=True)
                worker.start()
                import main
                worker.join(timeout=1)
                assert not worker.is_alive()
                assert not failure, failure
            """, temp_dir)

    def test_web_countdown_survives_reentering_same_battle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main
                from game_storage import load_data, save_data

                p = main.get_player("Тест", remember_player=False)
                p["marathon_route"][1]["mob_id"] = "cave_spider"
                p["marathon_route"][1]["mob_name"] = "Пещерный паук"
                p["task_num"] = 15
                p["web_seconds_left"] = 4.5
                save_data({"Тест": p})
                main.player_name = "Тест"
                main.player_data = p
                main.task_num = 15
                main.current_world_idx = 1
                main.start_mob_encounter()
                assert main.mob_web_seconds_left == 4.5
                main.mob_web_seconds_left = 2.25
                main.persist_mob_web_timer()
                assert load_data()["Тест"]["web_seconds_left"] == 2.25
            """, temp_dir)

    def test_spider_web_blocks_answers_but_not_marathon_clock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, threading, time, traceback, pygame
                from game_storage import load_data, save_data
                failure = []

                def play():
                    try:
                        deadline = time.time() + 12
                        while time.time() < deadline:
                            app = sys.modules.get("main")
                            if app and hasattr(app, "mob_answer_buttons") and app.game_state == "REGISTER":
                                break
                            time.sleep(.02)
                        else:
                            raise AssertionError("Game did not start")
                        p = app.get_player("Тест", remember_player=False)
                        p["marathon_route"][1]["mob_id"] = "cave_spider"
                        p["marathon_route"][1]["mob_name"] = "Пещерный паук"
                        p["task_num"] = 15
                        save_data({"Тест": p})
                        app.player_name = "Тест"
                        app.player_data = p
                        app.task_num = 15
                        app.current_world_idx = 1
                        app.step_in_world = 5
                        app.start_mob_encounter()
                        app.random.random = lambda: 0.0
                        wrong = next(i for i, answer in enumerate(app.mob_choices) if answer != app.mob_ans)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, pos=app.mob_answer_buttons[wrong].center, button=1))
                        while time.time() < deadline and app.mob_web_seconds_left <= 0:
                            time.sleep(.02)
                        assert app.mob_web_seconds_left > 0
                        assert load_data()["Тест"]["web_seconds_left"] > 0
                        hp_before = app.mob_hp
                        elapsed_before = app.marathon_elapsed_seconds
                        correct = app.mob_choices.index(app.mob_ans)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, pos=app.mob_answer_buttons[correct].center, button=1))
                        time.sleep(.15)
                        assert app.mob_hp == hp_before
                        while time.time() < deadline and app.marathon_elapsed_seconds <= elapsed_before:
                            time.sleep(.02)
                        assert app.marathon_elapsed_seconds > elapsed_before
                        app.mob_web_seconds_left = .01
                        while time.time() < deadline and app.mob_web_seconds_left > 0:
                            time.sleep(.02)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, pos=app.mob_answer_buttons[correct].center, button=1))
                        while time.time() < deadline and app.mob_hp == hp_before:
                            time.sleep(.02)
                        assert app.mob_hp < hp_before
                    except Exception as error:
                        failure.append(traceback.format_exc())
                    finally:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                worker = threading.Thread(target=play, daemon=True)
                worker.start()
                import main
                worker.join(timeout=3)
                assert not worker.is_alive()
                assert not failure, failure
            """, temp_dir)
