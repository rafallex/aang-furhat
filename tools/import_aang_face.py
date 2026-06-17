"""Install / update the custom Aang face on the robot. TWO mechanisms are needed:

  A) importCharacter (Studio WS, authenticated) -> creates the SELECTABLE character
     and sets its PROFILE (skin/eye/brow/lip choices, colours, face SHAPE). Applies live.
  B) /assetpack/deploy (HTTP) -> installs/updates the custom TEXTURE files (the skin
     with the baked-in arrow). Only takes effect after a ROBOT RESTART.

Recipe:
  python face/build_aang_face.py            # build face/Aang.zip (NAME is bumped per iteration)
  python tools/import_aang_face.py deploy    # A + B
  python tools/import_aang_face.py select    # apply profile live (lips/eyes/shape change now)
  >>> RESTART THE ROBOT <<<                  # loads the new skin texture (arrow)
  python tools/import_aang_face.py select    # select again after boot

Env: FURHAT_HOST, AANG_STUDIO_PASSWORD (default "admin"), AANG_CHAR_NAME (default "Aang2").
"""

import os
import sys
import json
import time
import base64
import hashlib

import requests
from websocket import create_connection

ROBOT = os.environ.get("FURHAT_HOST", "192.168.1.107")
PASSWORD = os.environ.get("AANG_STUDIO_PASSWORD", "admin")
NAME = os.environ.get("AANG_CHAR_NAME", "Aang4")
MASK = "adult"
FACE_ID = f"{MASK} - {NAME}"
ZIP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "face", "Aang.zip")

API_URL = f"ws://{ROBOT}:80/api"
RT_URL = f"ws://{ROBOT}:9000/v1/events"
DEPLOY_URL = f"http://{ROBOT}:80/assetpack/deploy"


def import_character():
    """A) Studio login + importCharacter -> selectable character + profile."""
    pw = hashlib.sha256(PASSWORD.encode()).hexdigest().upper()
    ws = create_connection(API_URL, timeout=20); ws.settimeout(4)

    def send(en, sid="", **f):
        m = {"event_name": en, "event_sessionId": sid}; m.update(f); ws.send(json.dumps(m))

    send("furhatos.event.actions.ActionRealTimeAPISubscribe", name="furhatos.event.monitors.MonitorLoginAccess")
    send("furhatos.event.requests.RequestSystemStatus")
    time.sleep(0.4)
    send("furhatos.event.actions.ActionLoginAccess", password=pw)
    sid = ""
    t = time.time()
    while time.time() - t < 10:
        try:
            m = json.loads(ws.recv())
        except Exception:
            continue
        if m.get("event_name") == "furhatos.event.monitors.MonitorLoginAccess":
            if m.get("loginApproved"):
                sid = m.get("event_sessionId", "")
            break
    if not sid:
        ws.close()
        raise RuntimeError(f"Studio login failed for password {PASSWORD!r} (set AANG_STUDIO_PASSWORD).")

    send("furhatos.event.actions.ActionRealTimeAPISubscribe", sid, name="furhatos.event.monitors.MonitorConfigFace")
    time.sleep(0.3)
    b64 = base64.b64encode(open(ZIP, "rb").read()).decode("ascii")
    imp = json.dumps({"data": b64, "name": NAME, "password": "", "mask": MASK, "overwrite": True})
    send("furhatos.event.actions.ActionConfigFace", sid, importCharacter=imp)
    confirms = 0
    t = time.time()
    while time.time() - t < 20:
        try:
            m = json.loads(ws.recv())
        except Exception:
            continue
        if m.get("event_name") == "furhatos.event.monitors.MonitorConfigFace":
            confirms += 1
    ws.close()
    return confirms


def assetpack_deploy():
    """B) HTTP asset-pack deploy -> custom textures (loaded on restart)."""
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
