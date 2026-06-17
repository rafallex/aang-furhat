"""The Avatar State: Aang's showpiece transformation and its theatrics.

enter()  -> freeze the face into the otherworldly stare, surge the LED ring to a
            breathing white glow, rise the head, swap to a deep booming voice,
            play the wind, and announce the awakening.
exit()   -> wind everything back down to the calm young monk.

While active, a background thread keeps the LED ring "breathing" so the glow
never looks static during conversation.
"""

import math
import time
import random
import threading

from .persona import ENTER_LINES, EXIT_LINES

# ----- palette -----
CALM_BLUE = "#2A6BC0"     # airbender calm (idle)
GLOW_CYAN = "#9BE8FF"     # spirit cyan
GLOW_WHITE = "#FFFFFF"    # full Avatar-State surge

# Head pitch (degrees) that makes the robot look *up* during the surge.
# Flip the sign if your unit looks down instead.
LOOK_UP_PITCH = 12.0

# The furious wide-eyed glare (stand-in until a custom glowing-eyes texture exists).
# Re-applied each turn by assert_look() so the stare never relaxes mid-rage.
AVATAR_STARE = {
    "EYE_WIDE_LEFT": 1.0, "EYE_WIDE_RIGHT": 1.0,
    "BROW_DOWN_LEFT": 1.0, "BROW_DOWN_RIGHT": 1.0,   # FURIOUS furrow, not a serene stare
    "BLINK_LEFT": 0.0, "BLINK_RIGHT": 0.0,
}


def scale_hex(hex_color, factor):
    """Scale an #RRGGBB color toward black by `factor` in [0, 1]."""
    factor = max(0.0, min(1.0, factor))
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(
        int(r * factor), int(g * factor), int(b * factor)
    )


class AvatarState:
    def __init__(self, furhat, cfg, sfx=None):
        self.f = furhat
        self.cfg = cfg
        self.sfx = sfx
        self.active = False
        self.entered_at = 0.0          # time.time() when the Avatar State last ignited
        self._glow_thread = None
        self._glow_stop = threading.Event()

    # ------------------------------------------------------------------ glow
    def _glow_loop(self):
        i = 0.0
        while not self._glow_stop.is_set():
            brightness = 0.6 + 0.4 * (0.5 * (1 + math.sin(i)))   # 0.6 .. 1.0
            self.f.led(scale_hex(GLOW_WHITE, brightness))
            i += 0.45
            time.sleep(0.06)

    # ------------------------------------------------------------------ enter
    def enter(self, brain=None, speak=True):
        if self.active:
            return
        self.active = True
        self.entered_at = time.time()
        f = self.f

        # 1. Cut whatever's happening, swap to the GLOWING avatar face, and freeze it.
        f.stop_speaking()
        f.listen_stop()
        f.system_config(volume=self.cfg.volume_avatar)   # louder, more thunderous
        f.face_config(face_id=self.cfg.face_id_avatar, blinking=False,
                      microexpressions=False, head_sway=False)

        # 2. Take manual control of the head (loose slack = we can pose it).
        f.attend_location(x=0.0, y=0.05, z=1.2, slack_yaw=30, slack_pitch=30, slack_timeout=-1)

        # 3. Snap the eyes wide — the glowing-eyes stand-in until a custom texture exists.
        f.led("#000000")
        f.face_params(AVATAR_STARE)

        # 4. The rushing wind.
        if self.sfx:
            try:
                f.speak_audio(self.sfx.url(), text="(wind)", lipsync=False, abort=True)
            except Exception:
                pass

        # 5. Slow rise of the head, eyes to the sky.
        f.headpose(pitch=LOOK_UP_PITCH, yaw=0.0, roll=0.0, speed="xslow")

        # 6. LED surge from black up to full.
        for k in range(0, 11):
            f.led(scale_hex(GLOW_WHITE, k / 10.0))
            time.sleep(0.09)

        # 7. Start the breathing glow.
        self._glow_stop.clear()
        self._glow_thread = threading.Thread(target=self._glow_loop, daemon=True)
        self._glow_thread.start()

        # 8. Deep voice + the awakening line.
        f.voice_config(voice_id=self.cfg.voice_avatar)
        time.sleep(0.15)
        f.headpose(pitch=LOOK_UP_PITCH * 0.35, speed="slow")  # settle, still elevated
        if speak:
            f.say_and_wait(random.choice(ENTER_LINES))

    # ------------------------------------------------------------------ exit
    def exit(self, speak=True):
        if not self.active:
            return
        self.active = False
        f = self.f

        # Stop the glow.
        self._glow_stop.set()
        if self._glow_thread:
            self._glow_thread.join(timeout=1.0)

        # No spoken exit line: in the show the Avatar State just SUBSIDES (no farewell in
        # the Avatar voice). He simply returns to himself — the conversation carries on as Aang.
        # (`speak` kept for signature compatibility; intentionally unused now.)

        # Restore the young monk.
        f.voice_config(voice_id=self.cfg.voice_normal)
        f.system_config(volume=self.cfg.volume)
        f.face_params({"EYE_WIDE_LEFT": 0.0, "EYE_WIDE_RIGHT": 0.0,
                       "BROW_DOWN_LEFT": 0.0, "BROW_DOWN_RIGHT": 0.0})
        f.face_reset()
        # back to the everyday Aang face
        f.face_config(face_id=self.cfg.face_id, blinking=True, microexpressions=True, head_sway=False)
        f.headpose(pitch=0.0, yaw=0.0, roll=0.0, speed="slow")
        f.attend_user("closest")

        # Fade the ring back to calm airbender blue.
        for k in range(10, -1, -1):
            f.led(scale_hex(GLOW_CYAN, k / 10.0))
            time.sleep(0.05)
        f.led(CALM_BLUE)

    # ------------------------------------------------------------------ self-heal
    def assert_look(self):
        """Re-assert the intended face each turn so a face-swap dropped over the network
        auto-corrects. While enraged, also re-apply the wide-eyed glare so it never relaxes
        mid-rage. Re-selecting the already-active face is a no-op, so there's no flicker."""
        if self.active:
            self.f.face_config(face_id=self.cfg.face_id_avatar, blinking=False, microexpressions=False)
            self.f.face_params(AVATAR_STARE)
        else:
            self.f.face_config(face_id=self.cfg.face_id, blinking=True, microexpressions=True)
