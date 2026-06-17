"""A small, synchronous client for the Furhat Realtime API.

The Realtime API is a single WebSocket at ws://<host>:9000/v1/events over which
you exchange JSON messages, each tagged with a `type` (e.g. "request.speak.text").
A background reader thread parses every incoming message into a queue; the main
thread drives the robot with the high-level helpers below and blocks on
`wait_for(...)` when it needs a specific response (e.g. end-of-speech).
"""

import sys
import json
import time
import queue
import threading

from websocket import (
    create_connection,
    WebSocketTimeoutException,
    WebSocketConnectionClosedException,
)


class FurhatRT:
    def __init__(self, host, port=9000, auth_key=None, verbose=True):
        self.url = f"ws://{host}:{port}/v1/events"
        self.auth_key = auth_key
        self.verbose = verbose
        self.scope = None
        self._ws = None
        self._send_lock = threading.Lock()
        self._events = queue.Queue()
        self._running = False
        self._reader = None
        self.alive = False        # False once the socket drops; the app reconnects

    # ------------------------------------------------------------------ lifecycle
    def connect(self, timeout=10):
        self._ws = create_connection(self.url, timeout=timeout)
        self._ws.settimeout(0.4)
        self._running = True
        self.alive = True
        self._reader = threading.Thread(target=self._read_loop, name="furhat-reader", daemon=True)
        self._reader.start()

        auth = {"type": "request.auth"}
        if self.auth_key:
            auth["key"] = self.auth_key
        self.send(auth)
        resp = self.wait_for("response.auth", timeout=5)
        if not resp or not resp.get("access"):
            raise RuntimeError(f"Furhat authentication failed/refused: {resp}")
        self.scope = resp.get("scope")
        return resp

    def close(self):
        self._running = False
        self.alive = False
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

    def reconnect(self, timeout=10):
        """Re-establish the WebSocket after a drop. Re-auths; returns the auth response."""
        try:
            self.close()
        except Exception:
            pass
        time.sleep(0.5)
        self._events = queue.Queue()
        return self.connect(timeout=timeout)

    def _read_loop(self):
        while self._running:
            try:
                raw = self._ws.recv()
            except WebSocketTimeoutException:
                continue
            except (WebSocketConnectionClosedException, OSError):
                break
            except Exception:
                break
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if self.verbose:
                t = msg.get("type", "")
                if msg.get("error") or t.startswith("error") or "error" in t:
                    print("[furhat error]", msg, file=sys.stderr)
            self._events.put(msg)

    # ------------------------------------------------------------------ io
    def send(self, payload):
        data = json.dumps(payload)
        try:
            with self._send_lock:
                self._ws.send(data)
        except Exception:
            self.alive = False   # socket dropped; the main loop will reconnect

    def drain(self):
        """Discard any buffered incoming events."""
        try:
            while True:
                self._events.get_nowait()
        except queue.Empty:
            pass

    def wait_for(self, types, timeout=10.0, on_other=None, tick=None):
        """Block until an event whose `type` is in `types` arrives.

        Returns the matching message, or None on timeout / tick-abort.
        `on_other(msg)` is called for every non-matching event; `tick()` is
        polled between reads and aborts the wait if it returns truthy.
        """
        if isinstance(types, str):
            types = (types,)
        types = set(types)
        end = time.time() + timeout
        while True:
            if tick and tick():
                return None
            remaining = end - time.time()
            if remaining <= 0:
                return None
            try:
                msg = self._events.get(timeout=min(0.2, remaining))
            except queue.Empty:
                continue
            if msg.get("type") in types:
                return msg
            if on_other:
                try:
                    on_other(msg)
                except Exception:
                    pass

    # ------------------------------------------------------------------ speak
    def say(self, text, abort=False, interruptable=False):
        self.send({"type": "request.speak.text", "text": text,
                   "abort": abort, "interruptable": interruptable})

    def say_and_wait(self, text, timeout=40, **kw):
        self.drain()
        self.say(text, **kw)
        self.wait_for("response.speak.end", timeout=timeout)

    def stop_speaking(self):
        self.send({"type": "request.speak.stop"})

    def speak_audio(self, url, text="(audio)", lipsync=False, abort=False):
        self.send({"type": "request.speak.audio", "url": url,
                   "text": text, "lipsync": lipsync, "abort": abort})

    def speak_audio_and_wait(self, url, text="(audio)", lipsync=True, abort=True, timeout=40):
        self.drain()
        self.speak_audio(url, text=text, lipsync=lipsync, abort=abort)
        self.wait_for("response.speak.end", timeout=timeout)

    # ------------------------------------------------------------------ gesture / face
    def gesture(self, name, intensity=1.0, duration=1.0):
        self.send({"type": "request.gesture.start", "name": name,
                   "intensity": intensity, "duration": duration})

    def face_config(self, face_id=None, visibility=None, microexpressions=None,
                    blinking=None, head_sway=None):
        p = {"type": "request.face.config"}
        if face_id is not None:
            p["face_id"] = face_id
        if visibility is not None:
            p["visibility"] = visibility
        if microexpressions is not None:
            p["microexpressions"] = microexpressions
        if blinking is not None:
            p["blinking"] = blinking
        if head_sway is not None:
            p["head_sway"] = head_sway
        self.send(p)

    def face_params(self, params):
        self.send({"type": "request.face.params", "params": params})

    def face_reset(self):
        self.send({"type": "request.face.reset"})

    def headpose(self, yaw=0.0, pitch=0.0, roll=0.0, relative=False, speed="medium"):
        self.send({"type": "request.face.headpose", "yaw": yaw, "pitch": pitch,
                   "roll": roll, "relative": relative, "speed": speed})

    # ------------------------------------------------------------------ voice
    def voice_config(self, voice_id=None, name=None):
        p = {"type": "request.voice.config"}
        if voice_id:
            p["voice_id"] = voice_id
        if name:
            p["name"] = name
        self.send(p)

    # ------------------------------------------------------------------ led
    def led(self, color):
        self.send({"type": "request.led.set", "color": color})

    def led_individual(self, leds, fill="#000000"):
        self.send({"type": "request.led.set.individual", "leds": leds, "fill": fill})

    # ------------------------------------------------------------------ attention / users
    def attend_user(self, user_id="closest"):
        self.send({"type": "request.attend.user", "user_id": user_id})

    def attend_location(self, x=0.0, y=0.0, z=1.0, slack_pitch=15, slack_yaw=5,
                        slack_timeout=3000, speed="medium"):
        self.send({"type": "request.attend.location", "x": x, "y": y, "z": z,
                   "slack_pitch": slack_pitch, "slack_yaw": slack_yaw,
                   "slack_timeout": slack_timeout, "speed": speed})

    def attend_nobody(self):
        self.send({"type": "request.attend.nobody"})

    def users_start(self):
        self.send({"type": "request.users.start"})

    def users_stop(self):
        self.send({"type": "request.users.stop"})

    # ------------------------------------------------------------------ system
    def system_config(self, volume=None):
        p = {"type": "request.system.config"}
        if volume is not None:
            p["volume"] = volume
        self.send(p)

    # ------------------------------------------------------------------ listen
    def listen_config(self, languages=None, phrases=None):
        p = {"type": "request.listen.config"}
        if languages is not None:
            p["languages"] = languages
        if phrases is not None:
            p["phrases"] = phrases
        self.send(p)

    def listen_start(self, **kw):
        p = {"type": "request.listen.start"}
        p.update(kw)
        self.send(p)

    def listen_stop(self):
        self.send({"type": "request.listen.stop"})

    def listen(self, timeout=12.0, no_speech_timeout=8.0, end_speech_timeout=1.0, tick=None):
        """Listen once. Returns the recognized text, or None on silence / abort."""
        self.drain()
        self.listen_start(partial=False, concat=True, stop_no_speech=True,
                          stop_robot_start=True, stop_user_end=True, resume_robot_end=False,
                          no_speech_timeout=no_speech_timeout, end_speech_timeout=end_speech_timeout)
        msg = self.wait_for(("response.hear.end", "response.listen.end"),
                            timeout=timeout, tick=tick)
        if msg is None:
            self.listen_stop()
            return None
        if msg.get("type") == "response.hear.end":
            return (msg.get("text") or "").strip() or None
        return None
