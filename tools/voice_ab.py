"""Render the SAME line two ways for an A/B listen: the Avatar FX deep voice
(edge-tts ChristopherNeural, pitch -30 Hz, rate -8%) vs the plain voice (same
voice, no pitch/rate change) that approximates the robot's native fallback.

Renders into a temp dir so it never litters the source folders.

Run:  python tools/voice_ab.py ["a line of text"] [out_dir]
"""
import os
import sys
import asyncio
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aang import avatar_voice_fx as fx


def render(text, out_dir, name, rate, pitch):
    os.makedirs(out_dir, exist_ok=True)
    mp3 = os.path.join(out_dir, name + ".mp3")
    raw = os.path.join(out_dir, name + "_raw.wav")
    out = os.path.join(out_dir, name + ".wav")
    asyncio.run(fx._tts(text, mp3, rate=rate, pitch=pitch))
    subprocess.run([fx._FFMPEG, "-y", "-i", mp3, "-ac", "1", "-ar", "24000", raw],
                   check=True, capture_output=True)
    seg = fx._read_wav(raw).normalize(headroom=3.0)
    fx._write_wav(seg, out)
    return out


line = sys.argv[1] if len(sys.argv) > 1 else \
    "You should not have done that. We are the Avatar, and your reckoning is here."
out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(tempfile.gettempdir(), "aang_voice_ab")

fx_wav = render(line, out_dir, "avatar_WITH_edge_fx_deep", rate="-8%", pitch="-30Hz")
plain_wav = render(line, out_dir, "avatar_WITHOUT_fx_plain", rate="+0%", pitch="+0Hz")
print("WITH edge-tts FX (-30 Hz, -8%):", fx_wav)
print("WITHOUT FX (plain Christopher) :", plain_wav)
