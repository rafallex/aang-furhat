"""Discover what a given Furhat has installed: auth scope, physical/virtual,
the full list of face_ids, and all available voices. Use this to pick a face
or voice for config.py / your .env.

Run:  python tools/probe.py            (filter voices: python tools/probe.py en-US)
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aang.config import Config
from aang.furhat import FurhatRT


def main():
    voice_filter = sys.argv[1].lower() if len(sys.argv) > 1 else None
    cfg = Config()
    f = FurhatRT(cfg.host, cfg.port, cfg.auth_key, verbose=False)
    resp = f.connect()
    print(f"AUTH: access={resp.get('access')} scope={resp.get('scope')}")

    f.send({"type": "request.system.status", "volume": True, "virtual": True})
    f.send({"type": "request.face.status", "face_id": True, "face_list": True})
    f.send({"type": "request.voice.status", "voice_id": True, "voice_list": True})

    seen = {}
    t0 = time.time()
    while time.time() - t0 < 6 and len(seen) < 3:
        msg = f.wait_for(("response.system.status", "response.face.status",
                          "response.voice.status"), timeout=2)
        if msg:
            seen[msg["type"]] = msg
    f.close()

    sysm = seen.get("response.system.status", {})
    print(f"SYSTEM: virtual={sysm.get('virtual')} volume={sysm.get('volume')}")

    facem = seen.get("response.face.status", {})
    faces = facem.get("face_list") or []
    print(f"\nFACES ({len(faces)})  current={facem.get('face_id')!r}")
    for name in faces:
        print("  ", name)

    voicem = seen.get("response.voice.status", {})
    voices = voicem.get("voice_list") or []
    print(f"\nVOICES ({len(voices)})  current={voicem.get('voice_id')!r}")
    for v in voices:
        vid = v.get("voice_id", "") if isinstance(v, dict) else str(v)
        if voice_filter and voice_filter not in vid.lower():
            continue
        print("  ", vid)


if __name__ == "__main__":
    main()
