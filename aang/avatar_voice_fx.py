"""Render the AVATAR-STATE voice: a SINGLE deep, DRY voice. We re-synthesize the line with
keyless neural TTS (edge-tts) and drop the engine's OWN pitch well below normal (~-30Hz) so
the depth is clean -- NO reverb, NO layered/detuned "chorus" copies. The old "chorus of past
lives + heavy reverb" was dropped: it doubled and sounded muddy on the robot's own speaker.

render(text) -> path to a WAV the robot can play via request.speak.audio (the audio FILE is
the voice; the text field is lip-sync only).

ffmpeg (from imageio-ffmpeg) is used ONLY to decode the mp3; all WAV I/O goes through the
stdlib `wave` module so pydub never needs ffprobe (which imageio doesn't ship).
"""

import os
import wave
import socket
import asyncio
import warnings
import functools
import threading
import subprocess
import http.server

import edge_tts
import imageio_ffmpeg

# imageio-ffmpeg ships a real ffmpeg, but NOT under the bare name "ffmpeg", so pydub's
# import-time PATH probe misses it and prints a RuntimeWarning. Point pydub straight at the
# imageio binary (and silence that one cosmetic warning). We still route all WAV I/O through
# the stdlib `wave` module, so ffprobe — which imageio doesn't ship — is never needed.
_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    from pydub import AudioSegment
AudioSegment.converter = _FFMPEG
AudioSegment.ffmpeg = _FFMPEG
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


async def _tts(text, mp3_path, voice=EDGE_VOICE, rate="-8%", pitch="-30Hz"):
    # Depth from the engine's OWN pitch (clean) -- not a pydub pitch-shift (that time-stretch
    # was the "prolonged echo"). rate slightly slow for gravitas without dragging.
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(mp3_path)


def render(text, name="avatar"):
    mp3 = os.path.join(OUT_DIR, name + ".mp3")
    raw = os.path.join(OUT_DIR, name + "_raw.wav")
    out = os.path.join(OUT_DIR, name + ".wav")
    asyncio.run(_tts(text, mp3))
    subprocess.run([_FFMPEG, "-y", "-i", mp3, "-ac", "1", "-ar", "24000", raw],
                   check=True, capture_output=True)
    main = _read_wav(raw)   # the deep voice -- depth comes from the TTS pitch (see _tts)

    # JUST the deep voice -- NO reverb. A faint reverb sounded fine on a PC but muddy/bad on the
    # robot's own speaker (and any echo on the robot reads as doubling). The deep TTS pitch IS
    # the whole effect. Single, clean, dry.
    mix = main.normalize(headroom=3.0)
    _write_wav(mix, out)
    return out


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else \
        "You should not have done that. We are the Avatar, and your reckoning is here."
    print(render(t))
