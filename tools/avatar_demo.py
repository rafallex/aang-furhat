"""One-shot Avatar State showpiece — no microphone or conversation needed.

Dresses the robot as Aang, runs the full Avatar State transformation (LED surge,
head-rise, wind, deep voice), holds it, then winds back down to the young monk.
Great for demos, and for verifying the whole choreography end to end.

Run:  python tools/avatar_demo.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aang.config import Config
from aang.furhat import FurhatRT
from aang.avatar_state import AvatarState, CALM_BLUE
from aang.lan_audio import LanAudioServer
from aang import sfx


def main():
    cfg = Config()
    f = FurhatRT(cfg.host, cfg.port, cfg.auth_key)
    print("connect:", f.connect().get("scope"))

    audio = None
    wind_url = None
    if cfg.sfx_enabled:
        try:
            audio = LanAudioServer(sfx.SFX_DIR, host=cfg.sfx_host, port=cfg.sfx_port)
            print("audio server at:", audio.start())
            wind_file = sfx.ensure_whoosh(audio.directory)
            if wind_file:
                wind_url = audio.url_for(wind_file)
        except Exception as e:
            print("SFX disabled:", e)

    avatar = AvatarState(f, cfg, wind_url=wind_url)

    # Dress as Aang.
    f.system_config(volume=cfg.volume)
    f.voice_config(voice_id=cfg.voice_normal)
    f.face_config(face_id=cfg.face_id, blinking=True, microexpressions=True, head_sway=False)
    f.users_start()
    f.attend_user("closest")
    f.led(CALM_BLUE)
    time.sleep(1.0)

    f.say_and_wait("Most days I'm just a kid who likes to fly. But when the world needs me...")

    print(">>> entering Avatar State")
    avatar.enter()
    f.say_and_wait("You took the Air Nomads from me - my people, my family. Now you face every Avatar who has ever lived!")
    time.sleep(1.5)

    print(">>> exiting Avatar State")
    avatar.exit()
    f.say_and_wait("Phew. That always takes a lot out of me. Wanna go penguin-sledding?")

    # cleanup
    f.face_reset()
    f.face_config(blinking=True, microexpressions=True)
    f.led("#000000")
    time.sleep(0.5)
    f.close()
    print("done")


if __name__ == "__main__":
    main()
