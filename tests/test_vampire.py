"""Vampire theft and the one-use bat follower in isolated save directories."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from game_content import MOB_ABILITIES, MOB_POOLS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VampireContentTests(unittest.TestCase):
    def test_vampire_is_a_nether_mob_with_bounded_theft(self):
        self.assertIn(("vampire", "Вампир"), MOB_POOLS[3])
        self.assertEqual(MOB_ABILITIES["vampire"]["kind"], "nether_mixed")
        self.assertEqual(MOB_ABILITIES["vampire"]["steal_amount"], 10)


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class VampireBehaviorTests(unittest.TestCase):
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

    def test_theft_clamps_bat_persists_and_expires_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main

                p = main.get_player("Тест", remember_player=False)
                assert not p["vampire_bat_active"]
                assert p["vampire_bat_target_world"] is None
                p["emeralds"] = 17
                assert main.steal_emeralds(p, 10) == 10
                assert main.steal_emeralds(p, 10) == 7
                assert p["emeralds"] == 0
                p["emeralds"] = 14
                p["vampire_bat_active"] = True
                p["vampire_bat_target_world"] = 4
                main.save_data({"Тест": p})

                reloaded = main.get_player("Тест", apply_daily_bonus=False, remember_player=False)
                assert reloaded["vampire_bat_active"]
                assert reloaded["vampire_bat_target_world"] == 4
                assert not main.release_vampire_bat_after_mob(reloaded, 3)
                assert main.trigger_vampire_bat(reloaded) == 10
                assert main.trigger_vampire_bat(reloaded) is None
                assert reloaded["emeralds"] == 4
                assert not reloaded["vampire_bat_active"]
                reloaded["vampire_bat_active"] = True
                reloaded["vampire_bat_target_world"] = 4
                assert main.release_vampire_bat_after_mob(reloaded, 4)
                assert not main.release_vampire_bat_after_mob(reloaded, 4)
                assert reloaded["emeralds"] == 4

                old_profile = dict(reloaded)
                old_profile.pop("vampire_bat_active")
                old_profile.pop("vampire_bat_target_world")
                main.save_data({"Тест": reloaded, "Старый": old_profile})
                migrated = main.get_player("Старый", apply_daily_bonus=False, remember_player=False)
                assert not migrated["vampire_bat_active"]
                assert migrated["vampire_bat_target_world"] is None

                reloaded["vampire_bat_active"] = True
                reloaded["vampire_bat_target_world"] = 4
                main.save_data({"Тест": reloaded, "Старый": migrated})
                main.player_name = "Тест"
                main.player_data = reloaded
                main.reset_entire_marathon()
                reset = main.load_data()["Тест"]
                assert not reset["vampire_bat_active"]
                assert reset["vampire_bat_target_world"] is None
            """, temp_dir)

    def test_wolf_chases_saved_bat_but_cannot_help_frog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main

                p = main.get_player("Тест", remember_player=False)
                p["vampire_bat_active"] = True
                p["vampire_bat_target_world"] = 4
                p["pet"] = "wolf"
                main.save_data({"Тест": p})
                p = main.get_player("Тест", apply_daily_bonus=False, remember_player=False)
                assert not p["vampire_bat_active"]
                assert p["vampire_bat_target_world"] is None

                p["vampire_bat_active"] = True
                p["vampire_bat_target_world"] = 4
                p["hero_frog"] = True
                assert not main.wolf_repels_vampire_bat(p)
                assert p["vampire_bat_active"]
                p["hero_frog"] = False
                assert main.wolf_repels_vampire_bat(p)
                assert not p["vampire_bat_active"]
                assert p["vampire_bat_target_world"] is None
            """, temp_dir)

    def test_wolf_repels_bat_after_vampire_victory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, pygame
                original_flip = pygame.display.flip
                frames = 0

                def click(rect):
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center
                    ))

                def flip():
                    global frames
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        p = app.get_player("Тест", remember_player=False)
                        p["emeralds"] = 25
                        p["pet"] = "wolf"
                        p["pet_errors"] = 0
                        p["artifacts"] = ["sharp_sword"]
                        p["artifact_charges"] = {"sharp_sword": 1}
                        p["marathon_route"][3]["mob_id"] = "vampire"
                        p["marathon_route"][3]["mob_name"] = "Вампир"
                        p["task_num"] = 35
                        app.save_data({"Тест": p})
                        app.player_name = "Тест"
                        app.player_data = p
                        app.task_num = 35
                        app.current_world_idx = 3
                        app.step_in_world = 5
                        app.start_mob_encounter()
                        assert app.mob_hp == 2
                    elif frames == 2:
                        wrong = next(i for i, answer in enumerate(app.mob_choices) if answer != app.mob_ans)
                        click(app.mob_answer_buttons[wrong])
                    elif frames == 3:
                        assert app.player_data["emeralds"] == 15
                        assert app.player_data["pet"] == "wolf"
                        click(app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)])
                    elif frames == 4:
                        assert app.mob_hp == 0
                        assert "Волк прогнал" in app.mob_battle_result_msg
                        app.mob_defeat_timer = 0
                        click(app.mob_btn_continue)
                    elif frames == 5:
                        saved = app.load_data()["Тест"]
                        assert saved["emeralds"] == 20
                        assert not saved["vampire_bat_active"]
                        assert saved["vampire_bat_target_world"] is None
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_buying_wolf_chases_existing_bat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, pygame
                original_flip = pygame.display.flip
                frames = 0

                def flip():
                    global frames
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        p = app.get_player("Тест", remember_player=False)
                        p["emeralds"] = 300
                        p["vampire_bat_active"] = True
                        p["vampire_bat_target_world"] = 4
                        app.save_data({"Тест": p})
                        app.player_name = "Тест"
                        app.player_data = p
                        app.game_state = "WORKBENCH"
                        app.workbench_tab = "PETS"
                        _, _, buy_button = app.get_shop_row_rects(0, len(app.PETS))
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=buy_button.center
                        ))
                    elif frames == 2:
                        p = app.load_data()["Тест"]
                        assert p["pet"] == "wolf"
                        assert p["emeralds"] == 60
                        assert not p["vampire_bat_active"]
                        assert p["vampire_bat_target_world"] is None
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_vampire_battle_steals_then_bat_steals_on_first_route_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, pygame
                original_flip = pygame.display.flip
                frames = 0

                def click(rect):
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center
                    ))

                def flip():
                    global frames
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        p = app.get_player("Тест", remember_player=False)
                        p["emeralds"] = 25
                        p["artifacts"] = ["sharp_sword"]
                        p["artifact_charges"] = {"sharp_sword": 1}
                        p["marathon_route"][3]["mob_id"] = "vampire"
                        p["marathon_route"][3]["mob_name"] = "Вампир"
                        p["task_num"] = 35
                        app.save_data({"Тест": p})
                        app.player_name = "Тест"
                        app.player_data = p
                        app.task_num = 35
                        app.current_world_idx = 3
                        app.step_in_world = 5
                        app.start_mob_encounter()
                        assert app.mob_hp == 2
                    elif frames == 2:
                        wrong = next(i for i, answer in enumerate(app.mob_choices) if answer != app.mob_ans)
                        click(app.mob_answer_buttons[wrong])
                    elif frames == 3:
                        assert app.player_data["emeralds"] == 15
                        click(app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)])
                    elif frames == 4:
                        assert app.mob_hp == 1
                        click(app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)])
                    elif frames == 5:
                        assert app.mob_hp == 0
                        assert not app.player_data["vampire_bat_active"]
                        app.mob_defeat_timer = 0
                        click(app.mob_btn_continue)
                    elif frames == 6:
                        saved = app.load_data()["Тест"]
                        assert saved["emeralds"] == 20
                        assert saved["vampire_bat_active"]
                        assert saved["vampire_bat_target_world"] == 4
                        assert app.game_state == "GAME"
                        wrong = next(i for i, answer in enumerate(app.choices) if answer != app.correct_ans)
                        click(app.answer_buttons[wrong])
                    elif frames == 7:
                        saved = app.load_data()["Тест"]
                        assert saved["emeralds"] == 10
                        assert not saved["vampire_bat_active"]
                        assert saved["vampire_bat_target_world"] is None
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_frog_wand_cancels_vampire_theft_and_bat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys, pygame
                original_flip = pygame.display.flip
                frames = 0

                def click(rect):
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center
                    ))

                def flip():
                    global frames
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        p = app.get_player("Тест", remember_player=False)
                        p["emeralds"] = 20
                        p["artifacts"] = ["frog_wand"]
                        p["artifact_charges"] = {"frog_wand": 1}
                        p["marathon_route"][3]["mob_id"] = "vampire"
                        p["marathon_route"][3]["mob_name"] = "Вампир"
                        p["task_num"] = 35
                        app.save_data({"Тест": p})
                        app.player_name = "Тест"
                        app.player_data = p
                        app.task_num = 35
                        app.current_world_idx = 3
                        app.step_in_world = 5
                        app.start_mob_encounter()
                    elif frames == 2:
                        click(app.mob_frog_btn)
                    elif frames == 3:
                        assert app.mob_hp == 1
                        wrong = next(i for i, answer in enumerate(app.mob_choices) if answer != app.mob_ans)
                        click(app.mob_answer_buttons[wrong])
                    elif frames == 4:
                        assert app.player_data["emeralds"] == 20
                        click(app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)])
                    elif frames == 5:
                        assert app.mob_hp == 0
                        app.mob_defeat_timer = 0
                        click(app.mob_btn_continue)
                    elif frames == 6:
                        saved = app.load_data()["Тест"]
                        assert saved["emeralds"] == 25
                        assert not saved["vampire_bat_active"]
                        pygame.event.post(pygame.event.Event(pygame.QUIT))

                pygame.display.flip = flip
                import main
            """, temp_dir)
