import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from array import array
from pathlib import Path

from game_content import WORLDS
from game_music import BIOME_TUNES, synthesize_biome_tune


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MusicSynthesisTests(unittest.TestCase):
    def test_each_biome_has_a_distinct_quiet_loop(self):
        self.assertEqual(len(BIOME_TUNES), len(WORLDS))
        loops = []
        for world_idx, (step_ms, _, notes) in enumerate(BIOME_TUNES):
            pcm = synthesize_biome_tune(world_idx, 22050, 1)
            self.assertEqual(len(pcm), round(22050 * step_ms / 1000) * len(notes) * 2)
            samples = array("h")
            samples.frombytes(pcm)
            self.assertEqual(samples[0], 0)
            self.assertEqual(samples[-1], 0)
            self.assertGreater(max(samples), 0)
            self.assertLess(max(abs(value) for value in samples), 8000)
            loops.append(pcm)
        self.assertEqual(len(set(loops)), len(WORLDS))

    def test_stereo_samples_are_identical_on_both_channels(self):
        samples = array("h")
        samples.frombytes(synthesize_biome_tune(0, 11025, 2))
        self.assertTrue(all(left == right for left, right in zip(samples[::2], samples[1::2])))


@unittest.skipUnless(importlib.util.find_spec("pygame"), "pygame is not installed")
class MusicPlaybackTests(unittest.TestCase):
    def test_biome_switch_sound_toggle_and_effect_channel(self):
        child_code = textwrap.dedent("""
            import pygame
            original_flip = pygame.display.flip
            def flip():
                original_flip()
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            pygame.display.flip = flip
            import main

            main.audio_attempted = False
            main.sound_enabled = True
            main.ensure_audio()
            assert main.music_channel is not None
            main.sync_biome_music(0, "GAME")
            assert main.music_world_idx == 0
            assert main.music_channel.get_busy()
            main.play_sound("correct")
            assert main.music_channel.get_busy()
            main.sync_biome_music(1, "MOB_BATTLE")
            assert main.music_world_idx == 1
            main.sound_enabled = False
            main.sync_biome_music(1, "GAME")
            assert main.music_world_idx is None
            main.sound_enabled = True
            main.sync_biome_music(1, "WORKBENCH")
            assert main.music_world_idx is None
            main.sync_biome_music(2, "BOSS_BATTLE")
            assert main.music_world_idx == 2
            pygame.mixer.quit()
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


if __name__ == "__main__":
    unittest.main()
