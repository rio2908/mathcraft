"""Bounded runtime caches plus a warmed-up Python/SDL memory soak test."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class MemoryTests(unittest.TestCase):
    def run_app(self, code, timeout=120):
        environment = os.environ.copy()
        environment.update({
            "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
            "PYGAME_HIDE_SUPPORT_PROMPT": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT),
        })
        bootstrap = """
            import asyncio
            original_run = asyncio.run
            asyncio.run = lambda coroutine: coroutine.close()
            import main as app
            asyncio.run = original_run
        """
        with tempfile.TemporaryDirectory() as directory:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", textwrap.dedent(bootstrap) + textwrap.dedent(code)],
                    cwd=directory, env=environment, capture_output=True, text=True,
                    errors="replace", timeout=timeout, check=False,
                )
            except subprocess.TimeoutExpired as error:
                self.fail(f"Memory workload timed out: {error.stderr!r}")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_login_button_cache_retains_only_the_visible_page(self):
        self.run_app("""
            import pygame
            for page in range(1000):
                names = [f'Kid-{page}-{row}' for row in range(3)]
                app.layout_login_profile_buttons(names)
                assert set(app.player_play_buttons) == set(names)
                assert set(app.player_stats_buttons) == set(names)
                assert set(app.player_delete_buttons) == set(names)
            app.layout_login_profile_buttons([])
            assert not app.player_play_buttons and not app.player_stats_buttons
            assert not app.player_delete_buttons
            pygame.quit()
        """)

    def test_timed_out_backup_screen_can_be_left_while_worker_is_stuck(self):
        self.run_app("""
            import os
            import pygame
            from types import SimpleNamespace
            app.game_state = 'BACKUP'
            app.backup_return_state = 'LOGIN'
            app.backup_picker._worker = SimpleNamespace(is_alive=lambda: True)
            frames = 0
            def flip():
                global frames
                frames += 1
                if frames == 1:
                    assert app.backup_picker.busy
                    assert 'Хранилище занято' in app.backup_picker.status
                    folder = os.environ.get('MC_TEST_SCREENSHOTS')
                    if folder:
                        pygame.image.save(app.screen, os.path.join(folder, 'backup-worker-busy.png'))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                        button=1, pos=app.backup_back_btn.center))
                elif frames == 2:
                    assert app.game_state == 'LOGIN'
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            pygame.display.flip = flip
            asyncio.run(app.main())
        """)

    def test_runtime_memory_plateaus_after_warmup(self):
        output = self.run_app("""
            import ctypes
            import gc
            import faulthandler
            import json
            import os
            import sys
            import tracemalloc
            import pygame
            faulthandler.dump_traceback_later(90, repeat=True)

            # Native Surface and Sound buffers are not covered by tracemalloc.
            # On Windows also sample current RSS and committed private bytes.
            if sys.platform == 'win32':
                class Counters(ctypes.Structure):
                    _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
                        (name, ctypes.c_size_t) for name in (
                            'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                            'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                psapi = ctypes.WinDLL('psapi', use_last_error=True)
                kernel.GetCurrentProcess.restype = ctypes.c_void_p
                psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]

            def process_memory():
                if sys.platform == 'win32':
                    info = Counters()
                    info.cb = ctypes.sizeof(info)
                    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
                        raise ctypes.WinError(ctypes.get_last_error())
                    return {'rss': info.WorkingSetSize, 'private': info.PrivateUsage}
                if os.path.exists('/proc/self/statm'):
                    with open('/proc/self/statm', encoding='ascii') as stream:
                        resident = int(stream.read().split()[1])
                    return {'rss': resident * os.sysconf('SC_PAGE_SIZE')}
                return {}

            frames_per_batch = max(100, int(os.environ.get('MATHCRAFT_MEMORY_FRAMES', '100')))
            trace_enabled = os.environ.get('MATHCRAFT_MEMORY_TRACE', '1') != '0'
            warmup = 180
            end = warmup + 3 * frames_per_batch
            profile = app.get_player('Memory', False, False)
            profile['game_history'] = [{'completed_at': '2026-10-16T12:00', 'errors': 0,
                                        'error_details': [], 'duration_seconds': 123}]
            app.save_data({'Memory': profile})
            app.known_profiles = ['Memory']
            app.saved_profiles = {'Memory': profile}
            app.enter_player('Memory')
            app.ensure_audio()
            for world in range(5):
                app.sync_biome_music(world, 'GAME')
            assert len(app.biome_music_sounds) == 5

            class FastClock:
                def tick(self, fps):
                    return 16
            app.clock = FastClock()
            states = ('LOGIN', 'HELP', 'MOB_CATALOG', 'WORKBENCH', 'GAME', 'MOB_BATTLE',
                      'SAGE_CHALLENGE', 'CHEST_LOCK', 'BOSS_BATTLE', 'REVIEW', 'FINAL_STATS',
                      'HISTORY', 'HISTORY_DETAIL', 'PARENT_PIN', 'PARENT_MENU', 'BACKUP',
                      'CONFIRM_RESET', 'CONFIRM_EXIT')
            measurements = []
            frame = 0
            resets = 0
            initial_snapshot = None
            original_flip = pygame.display.flip
            if trace_enabled:
                tracemalloc.start(1)

            def flip():
                global frame, resets, initial_snapshot
                original_flip()
                frame += 1
                if frame > end:
                    if frame >= end + 80:
                        assert not app.particles and not app.floating_texts
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    return
                assert len(app.particles) < 800, len(app.particles)
                assert len(app.floating_texts) < 100, len(app.floating_texts)
                assert len(app.biome_music_sounds) == 5
                assert len(app.game_sounds) == 5
                assert len(app.player_data['game_history']) == 1
                if frame >= warmup and (frame - warmup) % frames_per_batch == 0:
                    gc.collect()
                    if initial_snapshot is None and trace_enabled:
                        initial_snapshot = tracemalloc.take_snapshot()
                    measurements.append({'frame': frame, 'python': tracemalloc.get_traced_memory()[0] if trace_enabled else None,
                                         **process_memory()})
                if frame == end:
                    changes = tracemalloc.take_snapshot().compare_to(initial_snapshot, 'lineno') if trace_enabled else []
                    report = {'measurements': measurements, 'frames': end, 'resets': resets, 'tracemalloc': trace_enabled,
                              'retained_music_bytes': sum(len(sound.get_raw()) for sound in app.biome_music_sounds.values()),
                              'largest_python_changes': [str(item) for item in changes[:5]]}
                    print('MATHCRAFT_MEMORY ' + json.dumps(report))
                    return
                if frame % 100 == 0:
                    app.reset_entire_marathon()
                    resets += 1
                world = (frame // len(states)) % 5
                app.current_world_idx = world
                app.task_num = world * 10 + 1
                app.step_in_world = 1
                state = states[frame % len(states)]
                app.help_page = (frame // len(states)) % len(app.HELP_PAGES)
                app.mob_catalog_page = world
                app.workbench_tab = ('HELMETS', 'VEHICLES', 'ARTIFACTS', 'POTIONS', 'PETS')[world]
                app.history_selected_index = 0
                if state == 'MOB_BATTLE':
                    app.start_mob_encounter()
                elif state == 'BOSS_BATTLE':
                    app.start_boss_battle()
                elif state == 'SAGE_CHALLENGE':
                    app.start_sage_encounter()
                elif state == 'CHEST_LOCK':
                    app.start_chest_encounter()
                else:
                    app.game_state = state
                app.spawn_dust(400, 200)
                app.spawn_hit_sparks(400, 200)
                app.floating_texts.append(['+1', 400, 200, app.GREEN, 10])

            pygame.display.flip = flip
            asyncio.run(app.main())
        """, timeout=180)
        line = next(line for line in output.splitlines() if line.startswith("MATHCRAFT_MEMORY "))
        report = json.loads(line.removeprefix("MATHCRAFT_MEMORY "))
        measurements = report["measurements"]
        # Ignore warm-up and allocator high-water marks: compare two identical,
        # warmed workloads, with history length held fixed rather than deleted.
        first, last = measurements[1], measurements[-1]
        if first["python"] is not None:
            self.assertLess(last["python"] - first["python"], 1024 * 1024, report)
        if "private" in first:
            self.assertLess(last["private"] - first["private"], 8 * 1024 * 1024, report)
        self.assertGreater(report["resets"], 2)
        if os.environ.get("MATHCRAFT_MEMORY_REPORT"):
            print(json.dumps(report, indent=2))
