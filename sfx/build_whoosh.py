"""Build the Avatar-State wind/whoosh WAV (offline; needs numpy).

The wind is a committed static asset (sfx/whoosh.wav, force-tracked in git). At
runtime the app never regenerates it -- aang/lan_audio.py just serves the file.
Run this by hand ONLY when you want to retune the sound (length, pitch sweep, mix),
then commit the new whoosh.wav. Mirrors face/build_aang_face.py: the builder and
its committed asset live together in their own folder, outside the aang package.

Run:  python sfx/build_whoosh.py
"""

import os
import wave

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whoosh.wav")


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


if __name__ == "__main__":
    generate_whoosh(OUT)
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
