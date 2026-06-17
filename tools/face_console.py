"""Full manual control of Furhat's face, live.

The face is a back-projected *rigged* FaceCore model, not a pixel screen. You
control it by (1) turning off the autopilot and (2) driving facial parameters
yourself via request.face.params. This console lets you do that interactively.

Run:  python tools/face_console.py

Commands (type and press Enter):
  <PARAM> <value>     set a face parameter, e.g.  JAW_OPEN 0.8   or  GAZE_PAN -20
  pose <yaw> <pitch> <roll>   set head pose, e.g.  pose 0 12 0
  combo <P1> <v1> <P2> <v2> ...   set several params at once
  list                show known parameter names
  clear               zero everything you've set (face.reset)
  q                   restore the autopilot and quit

Notes:
  - Most params are 0.0 .. 1.0. GAZE_PAN/TILT are about -50 .. 50 (degrees-ish);
    NECK_PAN/TILT/ROLL similar. Values are held until you change them.
  - The full low-level set is the 52 ARKit blendshapes; the names below are the
    common high-level "BasicParams" plus gaze/neck. Any valid param name works,
    so you can type ARKit names too.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aang.config import Config
from aang.furhat import FurhatRT

KNOWN = {
    "expressions": ["EXPR_ANGER", "EXPR_DISGUST", "EXPR_FEAR", "EXPR_SAD",
                    "SMILE_CLOSED", "SMILE_OPEN", "SURPRISE"],
    "eyes / brows": ["BLINK_LEFT", "BLINK_RIGHT", "EYE_WIDE_LEFT", "EYE_WIDE_RIGHT",
                     "EYE_SQUINT_LEFT", "EYE_SQUINT_RIGHT", "BROW_UP_LEFT", "BROW_UP_RIGHT",
                     "BROW_DOWN_LEFT", "BROW_DOWN_RIGHT", "BROW_IN_LEFT", "BROW_IN_RIGHT",
                     "BROW_INNER_UP"],
    "mouth / jaw": ["JAW_OPEN", "SMILE_OPEN", "SMILE_CLOSED"],
    "phonemes (visemes for lipsync)": ["PHONE_AAH", "PHONE_B_M_P", "PHONE_BIGAAH",
                     "PHONE_CH_J_SH", "PHONE_D_S_T", "PHONE_EE", "PHONE_EH", "PHONE_F_V",
                     "PHONE_I", "PHONE_K", "PHONE_N", "PHONE_OH", "PHONE_OOH_Q",
                     "PHONE_R", "PHONE_TH", "PHONE_W"],
    "gaze / neck": ["GAZE_PAN", "GAZE_TILT", "NECK_PAN", "NECK_TILT", "NECK_ROLL"],
}


def print_known():
    for group, names in KNOWN.items():
        print(f"  {group}:")
        print("     " + "  ".join(names))


def main():
    cfg = Config()
    f = FurhatRT(cfg.host, cfg.port, cfg.auth_key)
    print("connect:", f.connect().get("scope"))

    # Take the face off autopilot so nothing fights your input.
    f.face_config(face_id=cfg.face_id, blinking=False, microexpressions=False, head_sway=False)
    f.attend_location(x=0.0, y=0.05, z=1.2, slack_yaw=60, slack_pitch=60, slack_timeout=-1)

    print(__doc__)
    state = {}  # accumulated params, re-sent merged so combos hold

    try:
        while True:
            try:
                line = input("face> ").strip()
            except EOFError:
                break
            if not line:
                continue
            parts = line.split()
            head = parts[0].lower()

            if head == "q":
                break
            if head == "list":
                print_known()
                continue
            if head == "clear":
                state = {}
                f.face_reset()
                print("  (reset)")
                continue
            if head == "pose" and len(parts) == 4:
                yaw, pitch, roll = map(float, parts[1:4])
                f.headpose(yaw=yaw, pitch=pitch, roll=roll, speed="fast")
                print(f"  pose yaw={yaw} pitch={pitch} roll={roll}")
                continue
            if head == "combo" and len(parts) >= 3:
                pairs = parts[1:]
                for i in range(0, len(pairs) - 1, 2):
                    state[pairs[i]] = float(pairs[i + 1])
                f.face_params(state)
                print(f"  {state}")
                continue
            # default: "<PARAM> <value>"
            if len(parts) == 2:
                try:
                    state[parts[0]] = float(parts[1])
                except ValueError:
                    print("  ! value must be a number")
                    continue
                f.face_params(state)
                print(f"  {parts[0]} = {parts[1]}")
                continue

            print("  ? unrecognized — try:  JAW_OPEN 0.8   |   pose 0 12 0   |   list   |   clear   |   q")
    finally:
        print("\nrestoring autopilot ...")
        f.face_reset()
        f.face_config(blinking=True, microexpressions=True, head_sway=False)
        f.attend_user("closest")
        f.close()


if __name__ == "__main__":
    main()
