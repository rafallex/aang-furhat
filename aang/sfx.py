"""Generates the Avatar-State wind/whoosh sound effect.

This module only PRODUCES the WAV; the shared LanAudioServer (see lan_audio.py)
is what actually serves it to the robot. Best-effort: if numpy isn't available
the file simply isn't (re)generated and the caller disables the wind.
"""

import os
import wave


WHOOSH_FILENAME = "whoosh.wav"
# Default home for the wind file: the repo ships a pre-generated copy here, so the
# wind still works on a machine without numpy. The app serves this directory.
SFX_DIR = os.path.join(os.path.dirname(__file__), "_sfx")


def generate_whoosh(path, seconds=3.4, sr=16000):
    """Write a rising wind + energy-surge WAV (mono, 16-bit, 16 kHz)."""
    import numpy as np

    n = int(seconds * sr)
    t = np.linspace(0, seconds, n, endpoint=False)

    # Swell envelope: slow attack, brief hold, gentle release.
    attack = np.clip(t / (seconds * 0.6), 0, 1) ** 1.4
    release = np.clip((seconds - t) / (seconds * 0.3), 0, 1)
    env = attack * np.minimum(1.0, release)

    # Wind: white noise smoothed into a low rushing band.
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    k = 220
    kernel = np.ones(k) / k
    wind = np.convolve(noise, kernel, mode="same")
    wind /= (np.max(np.abs(wind)) + 1e-9)

    # Energy surge: a low tone sweeping up in pitch as the state ignites.
    f0, f1 = 55.0, 190.0
    freq = f0 + (f1 - f0) * (t / seconds)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    surge = np.sin(phase)

    sig = (0.62 * wind + 0.38 * surge) * env
    sig /= (np.max(np.abs(sig)) + 1e-9)
    pcm = (sig * 32767 * 0.9).astype(np.int16)

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def ensure_whoosh(directory):
    """Make sure whoosh.wav exists in `directory`; return its filename (or None).

    If it's already there (e.g. the copy shipped in the repo) we keep it, so the
    wind works even without numpy. Returns None only if it's missing AND can't be
    generated -- the caller then just runs without the wind."""
    path = os.path.join(directory, WHOOSH_FILENAME)
    if not os.path.exists(path):
        try:
            generate_whoosh(path)
        except Exception:
            return None
    return WHOOSH_FILENAME
