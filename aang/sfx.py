"""Generates the Avatar State wind/whoosh sound and serves it over HTTP.

`request.speak.audio` plays a WAV from a URL that the *robot* fetches, so the
file is served from this PC on the LAN (not localhost). Best-effort: if numpy
isn't available or the port can't bind, the caller disables SFX and the rest of
the show carries on.
"""

import os
import wave
import socket
import struct
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


def detect_lan_ip():
    """Best guess at this machine's LAN IP (the address the robot can reach)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


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


class SFX:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = os.path.join(os.path.dirname(__file__), "_sfx")
        os.makedirs(self.dir, exist_ok=True)
        self.filename = "whoosh.wav"
        self.path = os.path.join(self.dir, self.filename)
        self.ip = cfg.sfx_host or detect_lan_ip()
        self.port = cfg.sfx_port
        self.httpd = None
        self._thread = None

    def url(self):
        return f"http://{self.ip}:{self.port}/{self.filename}"

    def start(self):
        if not os.path.exists(self.path):
            generate_whoosh(self.path)
        directory = self.dir

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=directory, **k)

            def log_message(self, *a):
                pass  # keep the console clean

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.url()

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()   # actually release the listening socket
            except Exception:
                pass
            if self._thread:
                self._thread.join(timeout=1.0)
            self.httpd = None
            self._thread = None
