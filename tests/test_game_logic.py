"""State-transition regressions and complete marathons in isolated saves."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


BOOTSTRAP = """
import asyncio
import pygame
original_run = asyncio.run
asyncio.run = lambda coroutine: coroutine.close()
import main as app
asyncio.run = original_run
app.sound_enabled = False
app.audio_attempted = True

class FastClock:
    def tick(self, fps):
        return 250

app.clock = FastClock()
def save(profile):
    profiles = app.load_data()
    profiles['Kid'] = profile
    app.save_data(profiles)
def click(rect):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
def stop():
    pygame.event.post(pygame.event.Event(pygame.QUIT))
"""


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class GameLogicTests(unittest.TestCase):
    def run_app(self, script):
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        })
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", textwrap.dedent(BOOTSTRAP) + textwrap.dedent(script)],
                cwd=directory, env=environment, capture_output=True, text=True,
                timeout=40, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_completed_marathon_does_not_keep_timing_on_reentry(self):
        self.run_app("""
            p = app.get_player('Kid', False, False)
            p.update(task_num=51, marathon_elapsed_seconds=123,
                     game_history=[{'duration_seconds': 123}])
            save(p)
            app.enter_player('Kid')
            frames = 0
            def flip():
                global frames
                frames += 1
                assert app.marathon_elapsed_seconds == 123, app.marathon_elapsed_seconds
                if frames == 12:
                    stop()
            pygame.display.flip = flip
            asyncio.run(app.main())
            assert app.load_data()['Kid']['marathon_elapsed_seconds'] == 123
            assert app.load_data()['Kid']['game_history'][-1]['duration_seconds'] == 123
        """)

    def test_movement_is_paused_in_menus_and_cannot_open_a_battle(self):
        for state, button in (("LOGIN", "nav_players"), ("WORKBENCH", "nav_workbench"),
                              ("CONFIRM_RESET", "nav_reset_game"), ("CONFIRM_EXIT", "nav_exit")):
            with self.subTest(state=state):
                self.run_app(f"""
                    p = app.get_player('Kid', False, False)
                    p['task_num'] = 3
                    p['marathon_route'][0]['mob_step'] = 3
                    p['sage_completed'] = True
                    save(p)
                    app.player_name = 'Kid'
                    app.player_data = p
                    app.task_num = 3
                    app.current_world_idx = 0
                    app.step_in_world = 3
                    app.game_state = 'GAME'
                    app.is_moving = True
                    app.move_progress = 0.8
                    app.target_x = app.platforms[3][0]
                    app.target_y = app.platforms[3][1] - 24
                    frames = 0
                    paused_progress = None
                    def flip():
                        global frames, paused_progress
                        frames += 1
                        if frames == 1:
                            paused_progress = app.move_progress
                            click(getattr(app, '{button}'))
                        elif frames <= 12:
                            assert app.game_state == '{state}', app.game_state
                            assert app.move_progress == paused_progress, app.move_progress
                            if frames == 12:
                                if '{state}' == 'WORKBENCH':
                                    click(pygame.Rect(30, 12, 100, 32))
                                else:
                                    stop()
                        elif frames == 20:
                            assert app.game_state == 'MOB_BATTLE', app.game_state
                            stop()
                    pygame.display.flip = flip
                    asyncio.run(app.main())
                """)

    def test_new_marathon_clears_combo_and_first_reward_is_one(self):
        self.run_app("""
            app.get_player('Kid', False, False)
            app.enter_player('Kid')
            app.combo_count = 12
            app.reset_entire_marathon()
            assert app.combo_count == 0, app.combo_count
            before = app.player_data['emeralds']
            frames = 0
            def flip():
                global frames
                frames += 1
                if frames == 1:
                    click(app.answer_buttons[app.choices.index(app.correct_ans)])
                elif frames == 2:
                    assert app.load_data()['Kid']['emeralds'] == before + 1
                    stop()
            pygame.display.flip = flip
            asyncio.run(app.main())
        """)

    def test_quit_from_login_does_not_clear_a_saved_heat_rune(self):
        self.run_app("""
            p = app.get_player('Kid', False, False)
            p.update(task_num=23, heat_rune_task=23, heat_rune_seconds_left=3.5,
                     heat_rune_mob_hp=2, heat_rune_regen_elapsed=1.5,
                     marathon_elapsed_seconds=88)
            save(p)
            app.player_name = 'Kid'
            app.player_data = p
            app.task_num = 23
            app.marathon_elapsed_seconds = 88
            app.game_state = 'LOGIN'
            pygame.display.flip = stop
            asyncio.run(app.main())
            restored = app.load_data()['Kid']
            assert restored['heat_rune_task'] == 23, restored
            assert restored['heat_rune_seconds_left'] == 3.5
            assert restored['heat_rune_mob_hp'] == 2
            assert restored['heat_rune_regen_elapsed'] == 1.5
        """)

    def test_timer_only_counts_active_tasks_and_battles(self):
        self.run_app("""
            app.task_num = 1
            app.player_data = {'chest_challenge': {'finished': False}}
            for state in app.TIMED_GAME_STATES:
                app.game_state = state
                assert app.marathon_timer_is_active(), state
            for state in ('LOGIN', 'WORKBENCH', 'REVIEW', 'FINAL_STATS',
                          'PARENT_PIN', 'PARENT_MENU', 'EMERALD_SETTINGS',
                          'CHALLENGE_SETTINGS', 'BACKUP', 'CONFIRM_EXIT', 'CONFIRM_RESET'):
                app.game_state = state
                assert not app.marathon_timer_is_active(), state
            app.game_state = 'MOB_BATTLE'
            app.mob_hp = 0
            assert not app.marathon_timer_is_active()
            app.mob_hp = 3
            app.mob_failed_reset = True
            assert not app.marathon_timer_is_active()
            app.game_state = 'SAGE_CHALLENGE'
            app.sage_finished = True
            assert not app.marathon_timer_is_active()
            app.game_state = 'CHEST_LOCK'
            app.player_data['chest_challenge']['finished'] = True
            assert not app.marathon_timer_is_active()
            app.game_state = 'BOSS_BATTLE'
            app.boss_won = True
            assert not app.marathon_timer_is_active()
            app.task_num = 51
            app.game_state = 'GAME'
            assert not app.marathon_timer_is_active()
            pygame.quit()
        """)

    def test_mob_and_boss_errors_are_saved_reviewed_and_in_final_history(self):
        self.run_app("""
            p = app.get_player('Kid', False, False)
            p.update(task_num=35, totems=0)
            p['marathon_route'][3].update(mob_id='blaze', mob_name='Ифрит', mob_step=5)
            save(p)
            app.enter_player('Kid')
            frames = 0
            expected = None
            def flip():
                global frames, expected
                frames += 1
                if frames == 1:
                    assert app.game_state == 'MOB_BATTLE'
                    wrong_index = next(i for i, value in enumerate(app.mob_choices) if value != app.mob_ans)
                    expected = (app.mob_clean_expr, app.mob_choices[wrong_index], app.mob_ans)
                    click(app.mob_answer_buttons[wrong_index])
                elif frames == 2:
                    p = app.load_data()['Kid']
                    assert p['marathon_errors'] == 1, p['marathon_errors']
                    error = p['marathon_error_details'][0]
                    assert (error['expr'], error['wrong'], error['correct']) == expected
                    assert error['source'] == 'mob'
                    assert p['boss_penalty_errors'] == 0
                    assert len(app.ten_errors) == 1
                    assert p['hero_hearts'] == 2
                    p['task_num'] = 50
                    save(p)
                    app.enter_player('Kid')
                    assert app.game_state == 'BOSS_BATTLE'
                    assert app.boss_clean_expr == expected[0], app.boss_clean_expr
                    assert len(app.boss_review_queue) == 1
                    wrong_index = next(i for i, value in enumerate(app.boss_choices) if value != app.boss_ans)
                    click(app.boss_answer_buttons[wrong_index])
                elif frames == 3:
                    p = app.load_data()['Kid']
                    assert p['marathon_errors'] == 2
                    assert p['marathon_error_details'][-1]['source'] == 'boss'
                    assert p['boss_penalty_errors'] == 0
                    app.boss_streak = app.boss_max_hp - 1
                    app.marathon_elapsed_seconds = 0.1
                    click(app.boss_answer_buttons[app.boss_choices.index(app.boss_ans)])
                elif frames == 4:
                    assert app.boss_won
                    p = app.load_data()['Kid']
                    assert p['game_history'][-1]['errors'] == 2
                    assert len(p['game_history'][-1]['error_details']) == 2
                    assert app.marathon_elapsed_seconds == p['marathon_elapsed_seconds'] == 1
                    stop()
            pygame.display.flip = flip
            asyncio.run(app.main())
            assert app.load_data()['Kid']['marathon_elapsed_seconds'] == 1
        """)

    def test_complete_marathons_visit_every_island_and_credit_one_day(self):
        for difficulty in ("easy", "hard"):
            with self.subTest(difficulty=difficulty):
                self.run_app(f"""
                    import random
                    random.seed(6)
                    p = app.get_player('Kid', False, False, difficulty='{difficulty}')
                    app.start_activity_challenge(p, 'Полный маршрут', 2)
                    save(p)
                    app.enter_player('Kid')
                    visited = set()
                    frames = 0
                    completed = 0
                    def flip():
                        global frames, completed
                        if completed >= 2:
                            return
                        frames += 1
                        assert frames < 4000, (app.game_state, app.task_num)
                        if app.game_state == 'GAME' and not app.is_moving:
                            assert app.task_num < 50, app.task_num
                            visited.add(app.task_num)
                            click(app.answer_buttons[app.choices.index(app.correct_ans)])
                        elif app.game_state == 'MOB_BATTLE':
                            if app.mob_hp > 0:
                                click(app.mob_answer_buttons[app.mob_choices.index(app.mob_ans)])
                            else:
                                app.mob_defeat_timer = 0
                                click(app.mob_btn_continue)
                        elif app.game_state == 'SAGE_CHALLENGE':
                            if app.sage_finished:
                                click(app.sage_continue_btn)
                            else:
                                click(app.sage_answer_buttons[app.sage_choices.index(app.sage_answer)])
                        elif app.game_state == 'CHEST_LOCK':
                            lock = app.player_data['chest_challenge']
                            if lock['finished']:
                                click(app.chest_continue_btn)
                            else:
                                click(app.chest_answer_buttons[lock['choices'].index(lock['answer'])])
                        elif app.game_state == 'REVIEW':
                            click(app.review_btn_continue)
                        elif app.game_state == 'BOSS_BATTLE':
                            if app.boss_won:
                                p = app.load_data()['Kid']
                                completed += 1
                                assert visited == set(range(1, 50)), visited
                                assert set(p['defeated_mob_worlds']) == set(range(5))
                                assert p['task_num'] == 51
                                assert len(p['game_history']) == completed
                                assert p['game_history'][-1]['errors'] == 0
                                assert p['game_history'][-1]['activity_challenge']['credited'] == (completed == 1)
                                assert p['activity_challenge']['count'] == 1
                                assert p['activity_challenge']['active']
                                if completed == 1:
                                    visited.clear()
                                    app.reset_entire_marathon()
                                else:
                                    stop()
                            else:
                                click(app.boss_answer_buttons[app.boss_choices.index(app.boss_ans)])
                    pygame.display.flip = flip
                    asyncio.run(app.main())
                """)
