"""Render the AVATAR-STATE voice: the show's effect is the actor's voice layered with
detuned copies (the chorus of past Avatars) plus heavy reverb. We generate neural TTS
(keyless, via edge-tts) and process it with pydub into that otherworldly, booming chorus.

render(text) -> path to a WAV the robot can play via request.speak.audio(lipsync=True).

ffmpeg (from imageio-ffmpeg) is used ONLY to decode the mp3; all WAV I/O goes through the
stdlib `wave` module so pydub never needs ffprobe (which imageio doesn't ship).
"""

import os
import wave
import socket
import asyncio
import functools
import threading
import subprocess
import http.server

import edge_tts
import imageio_ffmpeg
from pydub import AudioSegment
from pydub.effects import speedup

_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
EDGE_VOICE = os.environ.get("AANG_FX_VOICE", "en-US-ChristopherNeural")
OUT_DIR = os.environ.get("AANG_FX_DIR", os.path.join(os.environ.get("TEMP", "."), "aang_fx"))
os.makedirs(OUT_DIR, exist_ok=True)

# ---- tiny HTTP server so the robot can fetch the rendered WAVs (request.speak.audio) ----
_server = None
_base_url = None


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    finally:
        s.close()


def ensure_server(port=8079):
    """Start (once) an HTTP server serving OUT_DIR; return its base URL."""
    global _server, _base_url
    if _server is None:
        handler = functools.partial(_QuietHandler, directory=OUT_DIR)
        _server = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
        _server.daemon_threads = True
        threading.Thread(target=_server.serve_forever, daemon=True).start()
        _base_url = f"http://{_lan_ip()}:{port}"
    return _base_url


def url_for(name="avatar", bust=0):
    return f"{_base_url}/{name}.wav?t={bust}"


def _read_wav(path):
    with wave.open(path, "rb") as w:
        return AudioSegment(data=w.readframes(w.getnframes()),
                            sample_width=w.getsampwidth(),
                            frame_rate=w.getframerate(),
                            channels=w.getnchannels())


def _write_wav(seg, path):
    seg = seg.set_channels(1).set_sample_width(2).set_frame_rate(24000)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(seg.raw_data)


def _pitch(seg, semitones):
    rate = int(seg.frame_rate * (2.0 ** (semitones / 12.0)))
    return seg._spawn(seg.raw_data, overrides={"frame_rate": rate}).set_frame_rate(seg.frame_rate)


def _pitch_keep_time(seg, semitones):
    """Pitch-shift WITHOUT changing duration (so layers don't drone past the words)."""
    shifted = _pitch(seg, semitones)
    factor = 2.0 ** (-semitones / 12.0)   # how much longer _pitch made it
    if factor > 1.01:
        try:
            shifted = speedup(shifted, playback_speed=factor, chunk_size=120, crossfade=20)
        except Exception:
            pass
    return shifted


def _reverb(seg, taps=((105, -16), (200, -24))):   # just a hint of space, not a cavern
    out = seg
    for delay_ms, gain_db in taps:
        echo = (AudioSegment.silent(duration=delay_ms, frame_rate=seg.frame_rate) + seg).apply_gain(gain_db)
        out = out.overlay(echo)
    return out


async def _tts(text, mp3_path, voice=EDGE_VOICE, rate="-12%", pitch="-6Hz"):
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(mp3_path)


def render(text, name="avatar"):
    mp3 = os.path.join(OUT_DIR, name + ".mp3")
    raw = os.path.join(OUT_DIR, name + "_raw.wav")
    out = os.path.join(OUT_DIR, name + ".wav")
    asyncio.run(_tts(text, mp3))
    subprocess.run([_FFMPEG, "-y", "-i", mp3, "-ac", "1", "-ar", "24000", raw],
                   check=True, capture_output=True)
    base = _read_wav(raw)

    # Pitch the layers WITHOUT stretching time so nothing drones on past the words.
    lead = _pitch_keep_time(base, -2)                       # main voice, a touch deeper
    deep = _pitch_keep_time(base, -9).apply_gain(-7)        # quiet rumble underneath
    twin = (AudioSegment.silent(duration=22, frame_rate=base.frame_rate)
            + base).apply_gain(-7)                          # short-delayed double for chorus width

    n = max(len(lead), len(deep), len(twin))
    mix = AudioSegment.silent(duration=n + 260, frame_rate=base.frame_rate)
    mix = mix.overlay(lead).overlay(deep).overlay(twin)
    mix = _reverb(mix).normalize(headroom=3.0)
    _write_wav(mix, out)
    return out


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else \
        "You should not have done that. We are the Avatar, and your reckoning is here."
    print(render(t))
