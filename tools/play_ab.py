"""Play the two A/B voice WAVs on the Furhat speakers: the Avatar FX deep voice
vs the plain (no-FX) version. Serves them from a LanAudioServer (the robot fetches
over the LAN) and triggers request.speak.audio, with spoken labels in between.

Run:  python tools/play_ab.py [dir-with-the-wavs]
"""
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aang.config import Config
from aang.furhat import FurhatRT
from aang.lan_audio import LanAudioServer

AB_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "aang_voice_ab")
FX = "avatar_WITH_edge_fx_deep.wav"
PLAIN = "avatar_WITHOUT_fx_plain.wav"

cfg = Config()
f = FurhatRT(cfg.host, cfg.port, cfg.auth_key)
print("connect:", f.connect().get("scope"))
f.system_config(volume=cfg.volume)
f.voice_config(voice_id=cfg.voice_normal)   # normal voice for the spoken labels

audio = LanAudioServer(AB_DIR, host=cfg.sfx_host, port=cfg.sfx_port)
print("serving A/B dir at:", audio.start())
b = int(time.time())   # cache-bust so nothing stale replays

f.say_and_wait("First, the Avatar State voice, with the deep effect.")
time.sleep(0.3)
f.speak_audio_and_wait(audio.url_for(FX, bust=b), text="(avatar fx)", lipsync=True)
time.sleep(0.9)
f.say_and_wait("Now the same line, without the effect.")
time.sleep(0.3)
f.speak_audio_and_wait(audio.url_for(PLAIN, bust=b + 1), text="(plain)", lipsync=True)
time.sleep(0.5)
f.say_and_wait("That is the difference the effect makes.")

audio.stop()
f.close()
print("done")
