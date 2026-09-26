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
class ArtifactTests(unittest.TestCase):
    def run_app(self, script, workdir):
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

    def test_sword_is_drawn_only_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import asyncio
                asyncio.run = lambda coroutine: coroutine.close()
                import main
                import pygame

                hero = pygame.Surface((120, 120))
                hero.fill((0, 0, 0))
                main.draw_steve_animated(hero, 50, 60, "foot", False)
                assert hero.get_at((76, 34))[:3] == (0, 0, 0)

                hero.fill((0, 0, 0))
                main.draw_steve_animated(hero, 50, 60, "foot", False, show_sword=True)
                assert hero.get_at((76, 34))[:3] == (50, 220, 210)

                player = main.get_player("Без меча", remember_player=False)
                assert not main.has_active_artifact(player, "sharp_sword")
            """, temp_dir)

    def test_legacy_ownership_migrates_and_encounters_charge_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "mc_math_save.json"
            save_path.write_text(json.dumps({
                "Kid": {"artifacts": ["sharp_sword", "dragon_bow", "end_crystal"]}
            }), encoding="utf-8")
            self.run_app("""
                import pygame
                original_flip = pygame.display.flip
                def flip():
                    original_flip()
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main

                p = main.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                assert p["artifact_charges"] == {
                    "sharp_sword": 10, "dragon_bow": 3, "end_crystal": 2,
                }
                main.player_name = "Kid"
                main.player_data = p
                main.task_num = 3
                main.current_world_idx = 0
                main.start_mob_encounter()
                base_hp = main.MOB_ABILITIES[
                    main.get_route_world(main.player_data, 0)["mob_id"]
                ]["base_hp"]
                assert main.mob_max_hp == max(1, base_hp - 1)
                assert main.player_data["artifact_charges"]["sharp_sword"] == 9
                main.start_mob_encounter()
                assert main.player_data["artifact_charges"]["sharp_sword"] == 9

                main.start_boss_battle()
                assert main.boss_max_hp == 3
                assert main.player_data["artifact_charges"]["end_crystal"] == 1
                assert main.player_data["artifact_charges"]["dragon_bow"] == 3
                main.start_boss_battle()
                assert main.player_data["artifact_charges"]["end_crystal"] == 1
                assert main.artifact_repair_price("end_crystal", 1) == 70
            """, temp_dir)
            saved = json.loads(save_path.read_text(encoding="utf-8"))["Kid"]
            self.assertEqual(saved["artifact_charges"], {
                "sharp_sword": 9, "dragon_bow": 3, "end_crystal": 1,
            })

    def test_librarian_never_gifts_expensive_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import pygame
                original_flip = pygame.display.flip
                def flip():
                    original_flip()
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main

                p = main.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                main.grant_librarian_reward(p)
                assert p["sage_artifact"] in ("sharp_sword", "hint_book")
                assert p["artifact_charges"][p["sage_artifact"]] == 2
                artifact_id, name, description, status = main.librarian_reward_card(p)
                assert artifact_id == p["sage_artifact"]
                assert name == main.ARTIFACTS[artifact_id]["name"]
                assert description == main.ARTIFACTS[artifact_id]["desc"]
                assert "2/" in status
                main.grant_librarian_reward(p)
                assert set(p["artifacts"]) == {"sharp_sword", "hint_book"}
                for item in p["artifacts"]:
                    p["artifact_charges"][item] = main.ARTIFACTS[item]["max_charges"] - 1
                main.grant_librarian_reward(p)
                assert p["sage_artifact"].startswith("repair:")
                artifact_id, _, description, status = main.librarian_reward_card(p)
                assert artifact_id in ("sharp_sword", "hint_book")
                assert description == main.ARTIFACTS[artifact_id]["desc"]
                assert "Восстановлен 1 заряд" in status
                for item in p["artifacts"]:
                    p["artifact_charges"][item] = main.ARTIFACTS[item]["max_charges"]
                before = p["emeralds"]
                main.grant_librarian_reward(p)
                assert p["sage_artifact"] == "emeralds"
                assert p["emeralds"] == before + 10
                assert main.librarian_reward_card(p)[1] == "10 изумрудов"
            """, temp_dir)

    def test_shop_repairs_and_toggles_owned_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys
                import pygame
                original_flip = pygame.display.flip
                frames = 0
                def flip():
                    global frames
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        app.player_name = "Kid"
                        p = app.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                        p["artifacts"] = ["sharp_sword"]
                        p["artifact_charges"] = {"sharp_sword": 0}
                        p["emeralds"] = 100
                        app.save_data({"Kid": p})
                        app.player_data = p
                        app.game_state = "WORKBENCH"
                        app.workbench_tab = "ARTIFACTS"
                    elif frames == 2:
                        button = app.get_shop_row_rects(0, len(app.ARTIFACTS))[2]
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=button.center
                        ))
                    elif frames == 3:
                        p = app.load_data()["Kid"]
                        assert p["artifact_charges"]["sharp_sword"] == 10
                        assert p["emeralds"] == 40
                        button = app.get_artifact_toggle_rect(0)
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=button.center
                        ))
                    elif frames == 4:
                        assert "sharp_sword" in app.load_data()["Kid"]["disabled_artifacts"]
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_frog_wand_transforms_once_and_never_targets_dragon(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys
                import pygame
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
                        app.player_name = "Kid"
                        p = app.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                        p["artifacts"] = ["frog_wand"]
                        p["artifact_charges"] = {"frog_wand": 2}
                        p["marathon_route"][2]["mob_id"] = "ice_golem"
                        p["marathon_route"][2]["mob_name"] = "Ледяной голем"
                        app.save_data({"Kid": p})
                        app.player_data = p
                        app.task_num = 23
                        app.current_world_idx = 2
                        app.start_mob_encounter()
                    elif frames == 2:
                        click(app.mob_frog_btn)
                    elif frames == 3:
                        assert app.mob_hp == app.mob_max_hp == 1
                        assert app.player_data["frog_mob_task"] == 23
                        assert app.player_data["artifact_charges"]["frog_wand"] == 1
                        assert not app.mob_regen_started
                        app.start_mob_encounter()  # Resume the same encounter.
                        assert app.mob_hp == 1
                        assert app.player_data["artifact_charges"]["frog_wand"] == 1
                        click(app.mob_frog_btn)
                    elif frames == 4:
                        assert app.player_data["artifact_charges"]["frog_wand"] == 1
                        assert app.mob_hp == 1
                        answer = app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)]
                        click(answer)
                    elif frames == 5:
                        assert app.mob_hp == 0
                        app.mob_defeat_timer = 0
                        click(app.mob_btn_continue)
                    elif frames == 6:
                        assert app.load_data()["Kid"]["frog_mob_task"] is None
                        app.start_boss_battle()
                        click(app.mob_frog_btn)
                    elif frames == 7:
                        assert app.player_data["artifact_charges"]["frog_wand"] == 1
                        assert app.boss_streak == 0
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main
            """, temp_dir)

    def test_heat_rune_freezes_only_a_wounded_ice_golem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys
                import pygame

                class FastClock:
                    def tick(self, fps):
                        return 250

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
                        app.player_name = "Kid"
                        p = app.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                        p["artifacts"] = ["heat_rune"]
                        p["artifact_charges"] = {"heat_rune": 3}
                        p["marathon_route"][2]["mob_id"] = "ice_golem"
                        p["marathon_route"][2]["mob_name"] = "Ледяной голем"
                        app.save_data({"Kid": p})
                        app.player_data = p
                        app.task_num = 23
                        app.current_world_idx = 2
                        app.start_mob_encounter()
                        app.clock = FastClock()
                    elif frames == 2:
                        click(app.mob_heat_btn)  # Full health: no charge spent.
                    elif frames == 3:
                        assert app.player_data["artifact_charges"]["heat_rune"] == 3
                        answer = app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)]
                        click(answer)
                    elif frames == 4:
                        assert app.mob_hp == 2 and app.mob_regen_started
                        click(app.mob_heat_btn)
                    elif frames == 5:
                        assert app.player_data["artifact_charges"]["heat_rune"] == 2
                        assert app.mob_heat_seconds_left == 8.0
                        click(app.mob_heat_btn)  # Active rune cannot be stacked.
                    elif frames == 6:
                        assert app.player_data["artifact_charges"]["heat_rune"] == 2
                    elif frames == 20:
                        assert app.mob_hp == 2 and app.mob_heat_seconds_left > 0
                        assert app.mob_regen_elapsed < 0.5
                    elif frames == 38:
                        assert app.mob_hp == 2 and app.mob_heat_seconds_left == 0
                        assert app.mob_regen_elapsed < 1.0
                    elif frames == 54:
                        assert app.mob_hp == 3
                        assert app.load_data()["Kid"]["heat_rune_task"] is None
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main

                p = main.load_data()["Kid"]
                p["heat_rune_task"] = 23
                p["heat_rune_seconds_left"] = 3.5
                p["heat_rune_mob_hp"] = 2
                p["heat_rune_regen_elapsed"] = 1.5
                main.save_data({"Kid": p})
                main.start_mob_encounter()
                assert main.mob_heat_seconds_left == 3.5
                assert main.mob_hp == 2 and main.mob_regen_elapsed == 1.5
                assert main.player_data["artifact_charges"]["heat_rune"] == 2
            """, temp_dir)

    def test_book_click_hides_wrong_answer_and_uses_one_charge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.run_app("""
                import sys
                import pygame
                original_flip = pygame.display.flip
                frames = 0
                def flip():
                    global frames
                    original_flip()
                    frames += 1
                    app = sys.modules["main"]
                    if frames == 1:
                        app.player_name = "Kid"
                        p = app.get_player("Kid", apply_daily_bonus=False, remember_player=False)
                        p["artifacts"] = ["hint_book"]
                        p["artifact_charges"] = {"hint_book": 2}
                        route = p["marathon_route"]
                        route[0]["mob_id"] = "zombie"
                        route[0]["mob_name"] = "Зомби"
                        app.save_data({"Kid": p})
                        app.player_data = p
                        app.task_num = 3
                        app.current_world_idx = 0
                        app.start_mob_encounter()
                    elif frames == 2:
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=app.mob_book_btn.center
                        ))
                    elif frames == 3:
                        assert app.mob_hint_hidden >= 0
                        assert app.mob_choices[app.mob_hint_hidden] != app.mob_ans
                        assert app.player_data["artifact_charges"]["hint_book"] == 1
                        hidden = app.mob_answer_buttons[app.mob_hint_hidden]
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=hidden.center
                        ))
                    elif frames == 4:
                        assert app.mob_hp == 4
                        answer = app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)]
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN, button=1, pos=answer.center
                        ))
                    elif frames == 5:
                        assert app.mob_hp == 3
                        assert app.mob_hint_hidden == -1
                        assert app.load_data()["Kid"]["artifact_charges"]["hint_book"] == 1
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                pygame.display.flip = flip
                import main
            """, temp_dir)


if __name__ == "__main__":
    unittest.main()
