"""Avatar-State action server for the Furhat AI Creator.

The AI Creator character calls POST /avatar-state (per the action schema) when its
persona decides the moment is dire. This server then drives the REAL Avatar-State FX
on the robot over the Realtime API — glowing face swap, LED surge, furious glare,
deep voice — and AUTO-REVERTS to everyday Aang after a timeout, so the state never
sticks. It returns a short JSON the character can speak.

Run (in the furhat env):  python tools/avatar_action_server.py
Then point the action's server URL at  http://<this-pc-ip>:8088

Experimental: the AI Creator skill and the Realtime API both touch the face. The
character swap + LED hold well; the deep voice may get re-asserted by the skill on
its next utterance. The persona still makes it RAGE in words regardless.
"""

import json
import math
import time
import socket
import threading
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from websocket import create_connection

ROBOT = "192.168.1.107"
RT = f"ws://{ROBOT}:9000/v1/events"
PORT = 8088

FACE_NORMAL = "adult - Aang4"
FACE_AVATAR = "adult - Aang4Avatar"
VOICE_NORMAL = "Justin-Neural (en-US) - Amazon Polly"
VOICE_AVATAR = "Matthew-Neural (en-US) - Amazon Polly"
VOLUME_NORMAL = 60
VOLUME_AVATAR = 90    # boom louder in the Avatar State for drama
HOLD_SECONDS = 90.0   # safety net: auto-return even if the character never calls exit

_breath_stop = threading.Event()   # stops the pulsing "contained power" glow
_exit_timer = None                 # the safety auto-return timer


def _rt(commands):
    """Open a Realtime API connection, auth, send a list of command dicts, close."""
    ws = create_connection(RT, timeout=8)
    ws.settimeout(2)
    ws.send(json.dumps({"type": "request.auth"}))
    time.sleep(0.3)
    for c in commands:
        ws.send(json.dumps(c))
        time.sleep(0.02)
    time.sleep(0.2)
    ws.close()


def _breathe():
    """Pulse a blazing-white 'contained power' glow until exit is requested."""
    try:
        ws = create_connection(RT, timeout=8)
        ws.settimeout(2)
        ws.send(json.dumps({"type": "request.auth"}))
        time.sleep(0.3)
        i = 0
        while not _breath_stop.is_set():
            # smooth sine pulse between a strong glow (150) and full blaze (255)
            v = int(150 + 105 * (0.5 - 0.5 * math.cos(2 * math.pi * (i % 24) / 24.0)))
            try:
                ws.send(json.dumps({"type": "request.led.set",
                                    "color": "#{0:02X}{0:02X}{0:02X}".format(v)}))
            except Exception:
                break
            i += 1
            time.sleep(0.12)
        ws.close()
    except Exception:
        pass


def enter_avatar():
    global _exit_timer
    _breath_stop.set()                  # stop any prior glow loop
    time.sleep(0.15)
    _breath_stop.clear()

    cmds = [
        {"type": "request.system.config", "volume": VOLUME_AVATAR},
        {"type": "request.face.config", "face_id": FACE_AVATAR,
         "blinking": False, "microexpressions": False, "head_sway": False},
        {"type": "request.led.set", "color": "#000000"},
    ]
    # dramatic ignition: stark flicker -> deep rage-red builds -> blinding white erupts
    for _ in range(2):
        cmds += [{"type": "request.led.set", "color": "#FFFFFF"},
                 {"type": "request.led.set", "color": "#000000"}]
    cmds += [{"type": "request.led.set", "color": "#{0:02X}0000".format(int(255 * k / 8))}
             for k in range(0, 9)]                       # fury rises (black -> blood red)
    cmds += [{"type": "request.led.set", "color": "#{0:02X}{0:02X}{0:02X}".format(int(255 * k / 8))}
             for k in range(0, 9)]                       # power erupts (red -> blazing white)
    cmds += [
        # reliable fury: eyes wide, brows slammed down, never blink
        {"type": "request.face.params", "params": {
            "EYE_WIDE_LEFT": 1.0, "EYE_WIDE_RIGHT": 1.0,
            "BROW_DOWN_LEFT": 1.0, "BROW_DOWN_RIGHT": 1.0,
            "BLINK_LEFT": 0.0, "BLINK_RIGHT": 0.0}},
        # extra menace (sent separately so an unknown param can't drop the glare above)
        {"type": "request.face.params", "params": {
            "BROW_IN_LEFT": 1.0, "BROW_IN_RIGHT": 1.0,
            "SMILE_CLOSED_LEFT": -0.7, "SMILE_CLOSED_RIGHT": -0.7,
            "EXPR_ANGER": 1.0}},
        {"type": "request.voice.config", "voice_id": VOICE_AVATAR},
    ]
    _rt(cmds)

    threading.Thread(target=_breathe, daemon=True).start()
    if _exit_timer is not None:
        _exit_timer.cancel()
    _exit_timer = threading.Timer(HOLD_SECONDS, exit_avatar)
    _exit_timer.start()


def exit_avatar():
    global _exit_timer
    _breath_stop.set()                  # stop the glow loop
    if _exit_timer is not None:
        _exit_timer.cancel()
        _exit_timer = None
    time.sleep(0.15)
    _rt([
        {"type": "request.face.reset"},
        {"type": "request.face.config", "face_id": FACE_NORMAL,
         "blinking": True, "microexpressions": True},
        {"type": "request.voice.config", "voice_id": VOICE_NORMAL},
        {"type": "request.system.config", "volume": VOLUME_NORMAL},
        {"type": "request.led.set", "color": "#2A6BC0"},
    ])


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _trigger(self, reason):
        print(f"[avatar-action] triggered. reason={reason!r}")
        threading.Thread(target=enter_avatar, daemon=True).start()
        self._json({"status": "The Avatar State is unleashed.", "hold_seconds": HOLD_SECONDS})

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")
        if path == "/avatar-state/enter":
            q = parse_qs(urlparse(self.path).query)
            self._trigger((q.get("reason") or [""])[0])
        elif path == "/avatar-state/exit":
            print("[avatar-action] exit requested")
            threading.Thread(target=exit_avatar, daemon=True).start()
            self._json({"status": "The Avatar State subsides. Aang returns to himself."})
        else:
            self._json({"status": "ok"})   # health check

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            body = {}
        self._trigger(body.get("reason"))

    def log_message(self, *a):
        pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    finally:
        s.close()


if __name__ == "__main__":
    ip = lan_ip()
    print(f"Avatar-State action server on http://{ip}:{PORT}/avatar-state")
    print("Point the AI Creator action's server URL there.")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
