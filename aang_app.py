"""Aang on Furhat — the main show.

A full conversational Avatar (Listen -> LLM -> Speak) wearing the closest stock
face to a 12-year-old Air Nomad, who can unlock the AVATAR STATE either by a
spoken trigger phrase or a keyboard hotkey.

Run:   python aang_app.py
Keys:  [a] toggle the Avatar State    [q] quit

Speech triggers:
  auto  -> the LLM surges into the Avatar State on its own when stakes get dire
  enter -> "the world needs the avatar", "avatar state", "go avatar", ...
  exit  -> "come back Aang", "calm down", "that's enough", ...
  quit  -> "goodbye Aang", "shut down"
"""

import time
import random
import threading

from aang.config import Config
from aang.furhat import FurhatRT
from aang.brain import Brain
from aang.avatar_state import AvatarState, CALM_BLUE
from aang.persona import (
    OPENING_LINES, ENTER_LINES, TRIGGER_PHRASES, DEACTIVATE_PHRASES, QUIT_PHRASES,
    THINKING_GESTURES,
)
from aang import avatar_voice_fx as voicefx

try:
    import msvcrt  # Windows console key reader
except ImportError:
    msvcrt = None


class Keyboard(threading.Thread):
    """Non-blocking console hotkeys -> threading Events."""

    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.toggle_avatar = threading.Event()
        self.quit = threading.Event()

    def run(self):
        if not msvcrt:
            return
        while not self.quit.is_set():
            if msvcrt.kbhit():
                try:
                    ch = msvcrt.getwch().lower()
                except Exception:
                    ch = ""
                if ch == self.cfg.hotkey_avatar:
                    self.toggle_avatar.set()
                elif ch == self.cfg.hotkey_quit:
                    self.quit.set()
            time.sleep(0.04)


def matches(text, phrases):
    t = text.lower()
    return any(p in t for p in phrases)


def main():
    cfg = Config()
    print("=" * 60)
    print("  AANG on Furhat")
    print("=" * 60)

    f = FurhatRT(cfg.host, cfg.port, cfg.auth_key)
    print(f"Connecting to {cfg.host}:{cfg.port} ...")
    resp = f.connect()
    print(f"  connected (auth scope: {resp.get('scope')})")

    brain = Brain(cfg)
    print(f"Brain: {brain.describe()}")

    sfx = None
    if cfg.sfx_enabled:
        try:
            from aang.sfx import SFX
            sfx = SFX(cfg)
            print(f"SFX serving wind at {sfx.start()}")
        except Exception as e:
            print(f"SFX disabled ({e})")
            sfx = None

    avatar = AvatarState(f, cfg, sfx)

    # Avatar-State chorus voice: Christopher TTS layered with detuned copies + reverb,
    # rendered on the fly and served over HTTP for request.speak.audio.
    fx_ok = False
    try:
        fx_url = voicefx.ensure_server()
        fx_ok = True
        print(f"Avatar voice FX: {fx_url}")
    except Exception as e:
        print(f"Avatar voice FX disabled ({e}) - using plain TTS avatar voice")

    _fx_n = [0]

    def say_avatar(text):
        """Speak as the layered Avatar chorus; fall back to the TTS avatar voice."""
        if fx_ok:
            try:
                voicefx.render(text, "rage")
                _fx_n[0] += 1
                f.speak_audio_and_wait(voicefx.url_for("rage", _fx_n[0]), text=text, lipsync=True)
                return
            except Exception as e:
                print(f"  [fx] render failed ({e}); using TTS voice")
        f.say_and_wait(text)

    # --- dress the robot as Aang (also re-run after a reconnect) ---
    def dress():
        f.system_config(volume=cfg.volume)
        f.voice_config(voice_id=cfg.voice_normal)
        f.face_config(face_id=cfg.face_id, blinking=True, microexpressions=True, head_sway=False)
        f.users_start()
        f.attend_user("closest")
        f.listen_config(languages=["en-US"], phrases=TRIGGER_PHRASES + DEACTIVATE_PHRASES)
        f.led(CALM_BLUE)

    dress()
    print(f"Face: {cfg.face_id}  |  Voice: {cfg.voice_normal}")
    print("-" * 60)
    print(f"Controls:  [{cfg.hotkey_avatar}] Avatar State   [{cfg.hotkey_quit}] quit")
    print("-" * 60)

    kb = Keyboard(cfg)
    kb.start()

    f.gesture("BigSmile")
    f.say_and_wait(random.choice(OPENING_LINES))

    try:
        while not kb.quit.is_set():
            # Reconnect if the WebSocket dropped (robot blip / idle close).
            if not f.alive:
                print("  (connection dropped - reconnecting...)")
                try:
                    f.reconnect()
                    avatar.active = False     # robot is back to a clean state
                    dress()
                    print("  reconnected.")
                except Exception as e:
                    print(f"  reconnect failed ({e}); giving up.")
                    break
                continue

            # Hotkey takes priority.
            if kb.toggle_avatar.is_set():
                kb.toggle_avatar.clear()
                if avatar.active:
                    avatar.exit()
                else:
                    avatar.enter(brain, speak=False)
                    say_avatar(random.choice(ENTER_LINES))
                continue

            # The Avatar State burns out on its own — it never stays forever.
            if avatar.active and (time.time() - avatar.entered_at) > cfg.avatar_timeout:
                print("  (Avatar State burns out -> returning to Aang)")
                avatar.exit()
                continue

            text = f.listen(
                timeout=12.0,
                tick=lambda: kb.toggle_avatar.is_set() or kb.quit.is_set()
                or (avatar.active and (time.time() - avatar.entered_at) > cfg.avatar_timeout),
            )

            if kb.quit.is_set():
                break
            if kb.toggle_avatar.is_set():
                continue  # handled at top of loop
            if not text:
                continue

            print(f"  USER: {text}")

            if matches(text, QUIT_PHRASES):
                break
            # Manual overrides (explicit phrases) still work.
            if not avatar.active and matches(text, TRIGGER_PHRASES):
                avatar.enter(brain, speak=False)
                say_avatar(random.choice(ENTER_LINES))
                continue
            if avatar.active and matches(text, DEACTIVATE_PHRASES):
                avatar.exit()
                continue

            # Otherwise the LLM directs: each turn it decides whether the moment is
            # dire enough to surge into the Avatar State (or calm enough to leave it).
            if not avatar.active:
                f.gesture(random.choice(THINKING_GESTURES))
            want_avatar, reply = brain.respond(text, avatar=avatar.active)
            print(f"  AANG{' [AVATAR]' if want_avatar else ''}: {reply}")

            if want_avatar and not avatar.active:
                avatar.enter(brain, speak=False)   # surge into the Avatar State
            elif (not want_avatar) and avatar.active:
                avatar.exit(speak=False)           # recede to young Aang

            # rage lines speak as the layered Avatar chorus; everything else, normal voice
            (say_avatar if want_avatar else f.say_and_wait)(reply)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down ...")
        try:
            if avatar.active:
                avatar.exit()
            f.voice_config(voice_id=cfg.voice_normal)
            f.face_reset()
            f.face_config(blinking=True, microexpressions=True)
            f.led("#000000")
        except Exception:
            pass
        kb.quit.set()
        f.close()
        if sfx:
            sfx.stop()
        print("Goodbye. May the spirits watch over you.")


if __name__ == "__main__":
    main()
