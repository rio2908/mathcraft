"""Small original chiptune loops synthesized for the five game biomes."""

import math
from array import array


# MIDI pitches; None is a short breath before the next phrase.
BIOME_TUNES = (
    (350, (1.0, 0.16, 0.04),
     (60, 64, 67, 72, 67, 64, 62, None, 60, 64, 69, 72,
      69, 67, 64, None, 62, 65, 69, 74, 72, 69, 65, None)),
    (370, (1.0, 0.28, 0.08),
     (57, 60, 64, 69, 67, 64, 60, None, 55, 60, 64, 67,
      65, 64, 60, None, 57, 60, 64, 72, 69, 67, 64, None)),
    (430, (1.0, 0.38, 0.12),
     (72, 76, 79, None, 76, 74, 72, None, 69, 72, 76, None,
      79, 76, 72, None, 71, 74, 79, None, 81, 79, 74, None)),
    (320, (1.0, 0.25, 0.18),
     (48, 51, 55, 51, 48, None, 46, 48, 50, 53, 57, 53,
      50, None, 46, 48, 48, 55, 58, 55, 51, 48, None, None)),
    (410, (1.0, 0.14, 0.32),
     (60, 63, 67, 72, None, 70, 67, 63, 58, 62, 65, 70,
      None, 67, 65, 62, 60, 63, 67, 75, 72, 70, 67, None)),
)


def synthesize_biome_tune(world_idx, sample_rate, channels):
    """Return a signed 16-bit PCM loop matching the current mixer format."""
    if not 0 <= world_idx < len(BIOME_TUNES):
        raise ValueError("Unknown biome")
    if sample_rate <= 0 or channels <= 0:
        raise ValueError("Invalid audio format")

    step_ms, harmonics, notes = BIOME_TUNES[world_idx]
    step_samples = round(sample_rate * step_ms / 1000)
    fade_samples = max(1, round(sample_rate * 0.025))
    harmonic_total = sum(harmonics)
    samples = array("h")
    table_size = 1024
    waveform = tuple(
        (harmonics[0] * math.sin(phase)
         + harmonics[1] * math.sin(phase * 2)
         + harmonics[2] * math.sin(phase * 3)) / harmonic_total
        for phase in (2 * math.pi * index / table_size for index in range(table_size))
    )

    for note in notes:
        if note is None:
            samples.extend([0] * (step_samples * channels))
            continue
        frequency = 440.0 * 2 ** ((note - 69) / 12)
        phase_step = table_size * frequency / sample_rate
        phase = 0.0
        for sample_idx in range(step_samples):
            envelope = min(1.0, sample_idx / fade_samples,
                           (step_samples - sample_idx) / fade_samples)
            value = int(32767 * 0.16 * envelope * waveform[int(phase)])
            for _ in range(channels):
                samples.append(value)
            phase = (phase + phase_step) % table_size

    return samples.tobytes()
