import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import asyncio
import os
import pygame
run = asyncio.run
asyncio.run = lambda coroutine: coroutine.close()
import main as app
asyncio.run = run
app.audio_attempted = True

def click(rect):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
def stop():
    pygame.event.post(pygame.event.Event(pygame.QUIT))
def snapshot(name):
    folder = os.environ.get('MC_TEST_SCREENSHOTS')
    if folder:
        pygame.image.save(app.screen, os.path.join(folder, name + '.png'))
"""


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class ProfileManagementUITests(unittest.TestCase):
    def run_app(self, script):
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT),
        })
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-c", textwrap.dedent(BOOTSTRAP) + textwrap.dedent(script)],
                                    cwd=directory, env=environment, capture_output=True, text=True,
                                    timeout=25, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_icons_cancel_delete_selected_and_delete_last_profile_without_resurrection(self):
        self.run_app("""
            app.get_player('Настя', False, False)
            app.get_player('Ксения', False, False)
            app.enter_player('Настя')
            app.finish_marathon_to_menu()
            before = app.load_data()
            frames = 0
            def flip():
                global frames
                frames += 1
                if frames == 1:
                    assert set(app.player_delete_buttons) == {'Настя', 'Ксения'}
                    for name in app.player_play_buttons:
                        rects = (app.player_play_buttons[name], app.player_stats_buttons[name], app.player_delete_buttons[name])
                        assert all(pygame.Rect(0, 0, 1000, 600).contains(rect) for rect in rects)
                        assert not rects[0].colliderect(rects[1]) and not rects[1].colliderect(rects[2])
                    snapshot('players-icons')
                    click(app.player_stats_buttons['Настя'])
                elif frames == 2:
                    assert app.game_state == 'HISTORY'
                    click(app.history_back_btn)
                elif frames == 3:
                    click(app.create_profile_btn)
                elif frames == 4:
                    assert app.game_state == 'REGISTER'
                    click(app.register_back_btn)
                elif frames == 5:
                    assert app.game_state == 'LOGIN'
                    click(app.player_delete_buttons['Настя'])
                elif frames == 6:
                    assert app.game_state == 'CONFIRM_DELETE'
                    assert app.load_data() == before
                    snapshot('players-delete-confirm')
                    click(app.delete_confirm_no)
                elif frames == 7:
                    assert app.game_state == 'LOGIN' and app.load_data() == before
                    click(app.player_delete_buttons['Настя'])
                elif frames == 8:
                    click(app.delete_confirm_yes)
                elif frames == 9:
                    assert app.game_state == 'LOGIN'
                    assert app.load_data() == {'Ксения': before['Ксения']}
                    assert app.get_last_player() == 'Ксения'
                    assert app.player_name == '' and app.player_data == {}
                    assert set(app.player_delete_buttons) == {'Ксения'}
                    click(app.player_delete_buttons['Ксения'])
                elif frames == 10:
                    click(app.delete_confirm_yes)
                elif frames == 11:
                    assert app.game_state == 'REGISTER'
                    assert app.load_data() == {} and app.get_last_player() is None
                    assert not app.player_play_buttons and not app.player_stats_buttons and not app.player_delete_buttons
                    snapshot('players-empty')
                    stop()
            pygame.display.flip = flip
            run(app.main())
            assert app.load_data() == {}, 'Quit must not recreate a deleted profile'
        """)

    def test_delete_on_last_page_clamps_page_and_escape_preserves_progress(self):
        self.run_app("""
            for name in ('One', 'Two', 'Three', 'Four'):
                app.get_player(name, False, False)
            app.set_last_player('Four')
            app.known_profiles = list(app.load_data())
            app.login_show_all_players = True
            app.login_page = 1
            app.game_state = 'LOGIN'
            frames = 0
            def flip():
                global frames
                frames += 1
                if frames == 1:
                    assert set(app.player_delete_buttons) == {'Four'}
                    click(app.player_delete_buttons['Four'])
                elif frames == 2:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
                elif frames == 3:
                    assert app.game_state == 'LOGIN' and 'Four' in app.load_data()
                    click(app.player_delete_buttons['Four'])
                elif frames == 4:
                    click(app.delete_confirm_yes)
                elif frames == 5:
                    assert app.game_state == 'LOGIN' and app.login_page == 0
                    assert set(app.player_delete_buttons) == {'One', 'Two', 'Three'}
                    assert len(app.load_data()) == 3
                    stop()
            pygame.display.flip = flip
            run(app.main())
        """)

    def test_delete_waits_for_backup_and_displays_write_errors(self):
        self.run_app("""
            from types import SimpleNamespace
            app.get_player('Kid', False, False)
            app.game_state = 'LOGIN'
            frames = 0
            real_delete = app.delete_player
            def failing_delete(name):
                raise OSError('Не удалось удалить игрока.')
            def flip():
                global frames
                frames += 1
                if frames == 1:
                    click(app.player_delete_buttons['Kid'])
                elif frames == 2:
                    app.backup_picker._worker = SimpleNamespace(is_alive=lambda: True)
                    click(app.delete_confirm_yes)
                elif frames == 3:
                    assert app.game_state == 'CONFIRM_DELETE' and 'Kid' in app.load_data()
                    app.backup_picker._worker = None
                    app.delete_player = failing_delete
                    click(app.delete_confirm_yes)
                elif frames == 4:
                    assert app.game_state == 'CONFIRM_DELETE' and 'Kid' in app.load_data()
                    app.delete_player = real_delete
                    click(app.delete_confirm_no)
                elif frames == 5:
                    assert app.game_state == 'LOGIN'
                    stop()
            pygame.display.flip = flip
            run(app.main())
        """)

    def test_deleting_another_profile_preserves_current_player_and_timer(self):
        self.run_app("""
            kept = app.get_player('Keep', False, False)
            removed = app.get_player('Remove', False, False)
            kept.update(task_num=12, sage_task=None, emeralds=83)
            app.save_data({'Keep': kept, 'Remove': removed})
            app.enter_player('Keep')
            app.marathon_elapsed_seconds = 123.25
            app.persist_marathon_timer()
            app.finish_marathon_to_menu()
            before = app.load_data()['Keep']
            frames = 0
            def flip():
                global frames
                frames += 1
                if frames == 1:
                    click(app.player_delete_buttons['Remove'])
                elif frames == 2:
                    click(app.delete_confirm_yes)
                elif frames == 3:
                    assert app.game_state == 'LOGIN'
                    assert app.player_name == 'Keep' and app.task_num == 12
                    assert app.player_data['emeralds'] == 83
                    assert app.marathon_elapsed_seconds == 123.25
                    assert app.load_data() == {'Keep': before}
                    stop()
            pygame.display.flip = flip
            run(app.main())
            assert app.load_data() == {'Keep': before}
        """)

    def test_large_challenge_banner_fits_long_names(self):
        self.run_app("""
            rect = pygame.Rect(140, 376, 720, 136)
            for name in ('Большой семейный марафон', 'Ш' * 32, 'a' * 32):
                for completed in (False, True):
                    result = {'name': name, 'remaining': 0 if completed else 365, 'completed': completed,
                              'count': 365 if completed else 1, 'target_days': 365, 'credited': True}
                    profile = {'game_history': [{'activity_challenge': result}]}
                    lines = app.challenge_title_lines(name, app.FONT_TITLE, rect.width - 28)
                    assert ''.join(lines).replace(' ', '') == name.upper().replace(' ', '')
                    assert len(lines) <= 2
                    bounds = app.draw_challenge_banner(profile, rect)
                    assert bounds and all(rect.contains(bound) for bound in bounds), (name, bounds)
                    assert not rect.colliderect(app.boss_btn_stats)
                    assert not rect.colliderect(app.boss_btn_finish)
            assert app.draw_challenge_banner({}, rect) == []
            pygame.quit()
        """)

    def test_dragon_victory_shows_large_challenge_progress_and_completion(self):
        for goal, screenshot, name in (
            (3, "challenge-large-progress", "Семейное приключение"),
            (1, "challenge-large-complete", "Семейное приключение"),
            (365, "challenge-large-long-name", "Ш" * 32),
        ):
            with self.subTest(goal=goal):
                self.run_app(f"""
                    p = app.get_player('Kid', False, False)
                    app.start_activity_challenge(p, '{name}', {goal})
                    p['task_num'] = 50
                    app.save_data({{'Kid': p}})
                    app.enter_player('Kid')
                    app.boss_streak = app.boss_max_hp - 1
                    calls = []
                    real_banner = app.draw_challenge_banner
                    def banner(profile, rect):
                        bounds = real_banner(profile, rect)
                        calls.append((rect, bounds))
                        return bounds
                    app.draw_challenge_banner = banner
                    frames = 0
                    def flip():
                        global frames
                        frames += 1
                        if frames == 1:
                            click(app.boss_answer_buttons[app.boss_choices.index(app.boss_ans)])
                        elif frames == 2:
                            assert app.boss_won
                            result = app.load_data()['Kid']['game_history'][-1]['activity_challenge']
                            assert result['remaining'] == {goal - 1}
                            assert result['completed'] == ({goal} == 1)
                            assert calls and calls[-1][1]
                            assert all(calls[-1][0].contains(bound) for bound in calls[-1][1])
                            snapshot('{screenshot}')
                            click(app.boss_btn_finish)
                        elif frames == 3:
                            assert app.game_state == 'LOGIN'
                            stop()
                    pygame.display.flip = flip
                    run(app.main())
                """)
