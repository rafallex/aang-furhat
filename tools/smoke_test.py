"""Quick hardware check: drives every primitive Aang relies on, once, with
short pauses so you can watch the robot. Reverts to a neutral state at the end.

Run:  python tools/smoke_test.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aang.config import Config
from aang.furhat import FurhatRT


def main():
    cfg = Config()
    f = FurhatRT(cfg.host, cfg.port, cfg.auth_key)
    print("connect:", f.connect())

    print(f"face -> {cfg.face_id}")
    f.face_config(face_id=cfg.face_id, blinking=True, microexpressions=True)
    time.sleep(2.0)

    print(f"voice (normal) -> {cfg.voice_normal}")
    f.voice_config(voice_id=cfg.voice_normal)
    f.led("#2A6BC0")
    f.say_and_wait("Hi there! I'm Aang, and this is a quick systems check.")

    print("gesture -> BigSmile")
    f.gesture("BigSmile")
    time.sleep(1.5)

    # Headpose direction test: watch which way the head tilts.
    f.attend_location(z=1.2, slack_yaw=30, slack_pitch=30, slack_timeout=-1)
    print("headpose pitch = +12 (expecting: look UP)")
    f.headpose(pitch=12, speed="slow")
    time.sleep(2.0)
    print("headpose pitch = -12 (expecting: look DOWN)")
    f.headpose(pitch=-12, speed="slow")
    time.sleep(2.0)
    f.headpose(pitch=0, yaw=0, roll=0, speed="slow")
    time.sleep(1.0)

    print("face params -> wide eyes (Avatar-State stare)")
    f.face_params({"EYE_WIDE_LEFT": 1.0, "EYE_WIDE_RIGHT": 1.0,
                   "BROW_INNER_UP": 0.6, "BLINK_LEFT": 0.0, "BLINK_RIGHT": 0.0})
    time.sleep(2.5)
    f.face_reset()
    time.sleep(0.5)

    print(f"voice (avatar/deep) -> {cfg.voice_avatar}")
    f.voice_config(voice_id=cfg.voice_avatar)
    f.led("#FFFFFF")
    f.say_and_wait("We are the Avatar.")

    print("LED ramp test")
    for k in range(0, 11):
        f.led("#{0:02X}{0:02X}{0:02X}".format(int(255 * k / 10)))
        time.sleep(0.08)

    # revert
    f.voice_config(voice_id=cfg.voice_normal)
    f.face_reset()
    f.face_config(blinking=True, microexpressions=True)
    f.led("#000000")
    time.sleep(0.5)
    f.close()
    print("done — check stderr above for any [furhat error] lines")


if __name__ == "__main__":
    main()
