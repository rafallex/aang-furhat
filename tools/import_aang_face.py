"""Install / update the custom Aang face on the robot.

build_aang_face.py bundles BOTH the textures and the character profiles into
face/Aang.zip. This script ships that whole pack to the robot via the asset-pack
deploy (HTTP), then selects the face over the Realtime API. The pack carries the
profiles, so deploy + reboot is all that's needed -- no separate profile step.

Recipe:
  python face/build_aang_face.py            # build face/Aang.zip (NAME is bumped per iteration)
  python tools/import_aang_face.py deploy    # HTTP /assetpack/deploy -> textures + profiles
  >>> RESTART THE ROBOT <<<                  # asset packs load on boot
  python tools/import_aang_face.py select    # Realtime API -> wear "adult - Aang4"

Env: FURHAT_HOST, AANG_CHAR_NAME (default "Aang4").
"""

import os
import sys
import json
import time

import requests
from websocket import create_connection

ROBOT = os.environ.get("FURHAT_HOST", "192.168.1.107")
NAME = os.environ.get("AANG_CHAR_NAME", "Aang4")
MASK = "adult"
FACE_ID = f"{MASK} - {NAME}"
ZIP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "face", "Aang.zip")

RT_URL = f"ws://{ROBOT}:9000/v1/events"
DEPLOY_URL = f"http://{ROBOT}:80/assetpack/deploy"


def assetpack_deploy():
    """HTTP asset-pack deploy -> ships the whole pack (textures + profiles); loads on restart."""
    with open(ZIP, "rb") as fh:
        r = requests.post(DEPLOY_URL, data={"overwrite": "true"},
                          files={"assetpackzip": ("Aang.zip", fh, "application/zip")}, timeout=120)
    return r.text.strip()


def _rt():
    ws = create_connection(RT_URL, timeout=10); ws.settimeout(3)
    ws.send(json.dumps({"type": "request.auth"}))
    end = time.time() + 5
    while time.time() < end:
        try:
            if json.loads(ws.recv()).get("type") == "response.auth":
                break
        except Exception:
            pass
    return ws


def select():
    ws = _rt()
    ws.send(json.dumps({"type": "request.face.status", "face_id": True, "face_list": True}))
    faces, cur = [], None
    end = time.time() + 6
    while time.time() < end:
        try:
            m = json.loads(ws.recv())
        except Exception:
            continue
        if m.get("type") == "response.face.status":
            faces, cur = m.get("face_list") or [], m.get("face_id"); break
    print(f"current={cur!r}  |  Aang faces: {[f for f in faces if 'aang' in f.lower()]}")
    if FACE_ID not in faces:
        print(f"  {FACE_ID!r} not installed yet — run 'deploy' (and after a texture change, restart).")
        ws.close()
        return
    ws.send(json.dumps({"type": "request.face.config", "face_id": FACE_ID,
                        "blinking": True, "microexpressions": True}))
    ws.send(json.dumps({"type": "request.voice.config", "voice_id": "Justin-Neural (en-US) - Amazon Polly"}))
    ws.send(json.dumps({"type": "request.led.set", "color": "#2A6BC0"}))
    time.sleep(1.2)
    ws.close()
    print(f"  selected {FACE_ID!r} — look at the robot.")


def deploy():
    if not os.path.exists(ZIP):
        sys.exit("face/Aang.zip not found — run face/build_aang_face.py first.")
    # The pack contains BOTH characters and persists across restart. Asset packs are
    # singular (each deploy replaces the previous), which is why both faces are bundled.
    print("Deploying combined asset pack (adult - Aang4 + adult - Aang4Avatar) ...")
    print("  ", assetpack_deploy())
    print("\n  >>> RESTART THE ROBOT <<<  (asset packs load on boot), then:")
    print("      python tools/import_aang_face.py select")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "deploy"
    {"deploy": deploy, "select": select}.get(action, lambda: print("usage: deploy | select"))()
