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
    from pydub.effects import speedup
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


def _reverb(seg, taps=((100, -19), (185, -27))):   # a little space (mountain echo) - well short of the old cavern, no doubling
    out = seg
    for delay_ms, gain_db in taps:
        echo = (AudioSegment.silent(duration=delay_ms, frame_rate=seg.frame_rate) + seg).apply_gain(gain_db)
        out = out.overlay(echo)
    return out


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
    main = _read_wav(raw)   # main deep voice -- depth comes from the TTS pitch (see _tts)

    # The "SECOND WAVE": a much deeper, drawn-out ghost of the line that rolls back in as the
    # main line ENDS and trails off afterward (the chorus of past Avatars from the depths).
    # _pitch lowers pitch AND stretches time, so the ghost is naturally slow + cavernous. It
    # must start near the END of the line, never sit on top of it -- overlapping the main voice
    # is what sounds like a doubled "speaks twice". Tunables:
    GHOST_SEMITONES = -7      # how much DEEPER the ghost is (also = how drawn-out)
    GHOST_GAIN_DB   = -9      # how much QUIETER the ghost is
    GHOST_LEAD_MS   = 400     # ghost starts this many ms BEFORE the line ends
    GHOST_TAPS      = ((160, -20), (340, -28))   # cavern tail on the ghost only

    ghost  = _reverb(_pitch(main, GHOST_SEMITONES).apply_gain(GHOST_GAIN_DB), taps=GHOST_TAPS)
    delay  = max(0, len(main) - GHOST_LEAD_MS)
    second = AudioSegment.silent(duration=delay, frame_rate=main.frame_rate) + ghost

    n = max(len(main), len(second))
    mix = AudioSegment.silent(duration=n + 500, frame_rate=main.frame_rate)
    mix = mix.overlay(main).overlay(second).normalize(headroom=3.0)
    _write_wav(mix, out)
    return out


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else \
        "You should not have done that. We are the Avatar, and your reckoning is here."
    print(render(t))
