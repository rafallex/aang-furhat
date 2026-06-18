"""Aang on Furhat — the main show.

A full conversational Avatar (Listen -> LLM -> Speak) wearing the closest stock
face to a 12-year-old Air Nomad, who can unlock the AVATAR STATE either by a
spoken trigger phrase or a keyboard hotkey.

Run:   python aang_app.py
Keys:  [space] talk (push-to-talk)   [a] Avatar State   [q] quit

Speech triggers:
  auto  -> the LLM surges into the Avatar State on its own when stakes get dire
  enter -> "the world needs the avatar", "avatar state", "go avatar", ...
  exit  -> "come back Aang", "calm down", "that's enough", ...
  quit  -> "goodbye Aang", "shut down"
"""

import time
import re
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
        self.talk = threading.Event()
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
                elif ch == self.cfg.hotkey_talk:
                    self.talk.set()
                elif ch == self.cfg.hotkey_quit:
                    self.quit.set()
            time.sleep(0.04)


def matches(text, phrases):
    t = text.lower()
    return any(p in t for p in phrases)


def _echo_of(heard, said):
    """True if `heard` is really the robot hearing its own last line back
    (the mic and speaker share the head). Compares word overlap."""
    hw = set(re.findall(r"[a-z']+", heard.lower()))
    sw = set(re.findall(r"[a-z']+", said.lower()))
    if not hw or not sw:
        return False
    return len(hw & sw) / len(hw) >= 0.6


def _first_sentence(text):
    """Keep an Avatar reply to ONE punchy line. The model sometimes tags [AVATAR], lands the
    rage line, then slips back into a calm/worried Aang sentence in the same reply -- which
    makes him 'speak a full second time'. Cut at the first sentence-ending . ! or ?."""
    t = text.strip()
    m = re.search(r"[.!?](\s|$)", t)
    return t[:m.start() + 1] if m else t


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

    # Avatar-State voice. Default: render a deep "second wave" FX file (avatar_voice_fx.render
    # -- the main deep voice + a much deeper ghost that rolls back in AFTER the line) and play
    # it via request.speak.audio (the FILE is the voice; text=<line> is lip-sync only). Needs
    # the robot to fetch the file from this PC (works on Ethernet). Falls back to the robot's
    # plain native deep voice if rendering/playback fails or AANG_AVATAR_FX=0.
    fx_ok = False
    if cfg.avatar_voice_fx:
        try:
            fx_url = voicefx.ensure_server()
            fx_ok = True
            print(f"Avatar voice FX (second wave): {fx_url}")
        except Exception as e:
            print(f"Avatar voice FX disabled ({e}) - using native deep voice")

    _fx_n = [0]

    def say_avatar(text):
        # Cut the 3.4s surge wind + clear its speak.end first, or *_and_wait latches onto the
        # WIND's end and the line clips mid-sentence.
        if fx_ok:
            try:
                voicefx.render(text, "rage")
                _fx_n[0] += 1
                f.stop_speaking()
                time.sleep(0.2)
                f.drain()
                f.speak_audio_and_wait(voicefx.url_for("rage", _fx_n[0]), text=text, lipsync=True)
                return
            except Exception as e:
                print(f"  [fx] failed ({e}); using native voice")
        f.stop_speaking()
        time.sleep(0.2)
        f.drain()
        f.say_and_wait(text)

    # --- dress the robot as Aang (also re-run after a reconnect) ---
    def dress():
        f.listen_stop()  # clear any dangling listen session (e.g. left by a killed instance) -> stops "already listening" + early self-hearing
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
    talk_label = "space" if cfg.hotkey_talk == " " else cfg.hotkey_talk
    print(f"Mode: {'push-to-talk' if cfg.push_to_talk else 'open-mic'}")
    if cfg.push_to_talk:
        print(f"Controls:  [{talk_label}] talk   [{cfg.hotkey_avatar}] Avatar State   [{cfg.hotkey_quit}] quit")
    else:
        print(f"Controls:  [{cfg.hotkey_avatar}] Avatar State   [{cfg.hotkey_quit}] quit")
    print("-" * 60)

    kb = Keyboard(cfg)
    kb.start()

    f.gesture("BigSmile")
    last_said = random.choice(OPENING_LINES)
    f.say_and_wait(last_said)

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
                    last_said = random.choice(ENTER_LINES)
                    say_avatar(last_said)
                continue

            # The Avatar State burns out on its own — it never stays forever.
            if avatar.active and (time.time() - avatar.entered_at) > cfg.avatar_timeout:
                print("  (Avatar State burns out -> returning to Aang)")
                avatar.exit()
                continue

            # Push-to-talk: keep the mic CLOSED until you press the talk key, so the robot
            # can't hear itself (the open mic + shared head was the #1 demo gremlin). The
            # mic opens for exactly one utterance, then closes again while Aang thinks and
            # speaks. Open-mic mode (AANG_PTT=0) keeps the old always-listening loop.
            if cfg.push_to_talk and not kb.talk.is_set():
                time.sleep(0.05)
                continue
            kb.talk.clear()

            # Self-heal the face: re-assert the intended face (and the furious stare) so a
            # face-swap dropped over the network auto-corrects and the glare never relaxes.
            avatar.assert_look()

            if not cfg.push_to_talk:
                # Open mic only: let Aang's voice + room echo clear before the mic reopens.
                time.sleep(0.7)
            else:
                print("  (listening — speak now)")

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

            # Drop the robot hearing its own last line back (mic + speaker share the head).
            if _echo_of(text, last_said):
                print(f"  (ignored self-echo: {text})")
                continue

            print(f"  USER: {text}")

            if matches(text, QUIT_PHRASES):
                break
            # Manual overrides (explicit phrases) still work.
            if not avatar.active and matches(text, TRIGGER_PHRASES):
                avatar.enter(brain, speak=False)
                last_said = random.choice(ENTER_LINES)
                say_avatar(last_said)
                continue
            if avatar.active and matches(text, DEACTIVATE_PHRASES):
                avatar.exit()
                continue

            # Otherwise the LLM directs: each turn it decides whether the moment is
            # dire enough to surge into the Avatar State (or calm enough to leave it).
            if not avatar.active:
                f.gesture(random.choice(THINKING_GESTURES))
            want_avatar, reply = brain.respond(text, avatar=avatar.active)
            if want_avatar:
                reply = _first_sentence(reply)   # Avatar speaks ONE line -- no slipping back to calm Aang mid-reply
            print(f"  AANG{' [AVATAR]' if want_avatar else ''}: {reply}")

            if want_avatar and not avatar.active:
                avatar.enter(brain, speak=False)   # surge into the Avatar State
            elif (not want_avatar) and avatar.active:
                avatar.exit(speak=False)           # recede to young Aang

            # rage lines speak as the layered Avatar chorus; everything else, normal voice
            last_said = reply
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
