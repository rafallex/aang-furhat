"""Offline self-test for the Aang code (no physical robot needed).

Exercises everything except the live robot WebSocket: module imports, the merged
LanAudioServer (including the render -> serve path say_avatar uses), the committed
wind served by lan_audio, the brain fallback (+ a live groq call if GROQ_API_KEY is set), and
AvatarState.enter()/exit() against a stub robot. Run after any change to catch
breakage before touching the robot. Renders into temp dirs so it never litters
the served sfx/ folder.

Run:  python tools/selftest.py
"""
import os
import sys
import time
import tempfile
import importlib
import traceback
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []  # (status, name, detail)   status in {"PASS","FAIL","SKIP"}


class Skip(Exception):
    pass


def check(name, fn):
    try:
        fn(); results.append(("PASS", name, "")); print(f"[PASS] {name}")
    except Skip as s:
        results.append(("SKIP", name, str(s))); print(f"[SKIP] {name}: {s}")
    except Exception as e:
        results.append(("FAIL", name, repr(e))); print(f"[FAIL] {name}: {e}")
        traceback.print_exc()


def t_imports():
    for m in ["aang.config", "aang.furhat", "aang.brain", "aang.persona",
              "aang.avatar_state", "aang.avatar_voice_fx",
              "aang.lan_audio", "aang_app"]:
        importlib.import_module(m)
check("import every module (including aang_app)", t_imports)

from aang.config import Config
from aang.brain import Brain
from aang.avatar_state import AvatarState
from aang.lan_audio import LanAudioServer
from aang import avatar_voice_fx as voicefx

cfg = Config()


def t_server():
    d = tempfile.mkdtemp(prefix="aang_test_")
    with open(os.path.join(d, "ping.wav"), "wb") as fh:
        fh.write(b"\0" * 2048)
    srv = LanAudioServer(d, host="127.0.0.1", port=8126); srv.start()
    with urllib.request.urlopen(srv.url_for("ping.wav"), timeout=5) as r:
        data = r.read()
    assert r.status == 200 and len(data) == 2048, (r.status, len(data))
    assert srv.url_for("rage.wav", bust=7).endswith("rage.wav?t=7")
    srv.stop()
check("LanAudioServer serves a file over HTTP", t_server)


def t_wind():
    # The wind is a committed asset served by lan_audio -- no runtime generation.
    from aang.lan_audio import WIND_FILENAME
    srv = LanAudioServer(host="127.0.0.1", port=8128); srv.start()
    try:
        url = srv.wind_url()
        assert url and url.endswith(WIND_FILENAME), url
        with urllib.request.urlopen(url, timeout=5) as r:
            n = len(r.read())
        assert r.status == 200 and n > 1000, (r.status, n)
    finally:
        srv.stop()
check("lan_audio serves the committed wind (whoosh.wav)", t_wind)


def t_brain_fallback():
    c = Config(); c.brain_provider = "none"
    want, text = Brain(c).respond("hello there", avatar=False)
    assert isinstance(want, bool) and text.strip()
check("Brain 'none' fallback respond()", t_brain_fallback)


def t_brain_groq():
    if not os.environ.get("GROQ_API_KEY"):
        raise Skip("GROQ_API_KEY not set")
    b = Brain(Config())
    if b.provider != "groq":
        raise Skip("provider downgraded (no key)")
    _, text = b.respond("Reply with a short hello.", avatar=False)
    assert text.strip()
check("Brain live groq call", t_brain_groq)


def t_avatar_state():
    calls = []
    class StubF:
        def __getattr__(self, name):
            def rec(*a, **k):
                calls.append(name)
            return rec
    av = AvatarState(StubF(), cfg, wind_url="http://127.0.0.1:9/whoosh.wav")
    av.enter(); assert av.active
    time.sleep(0.2)
    av.exit(); assert not av.active
    assert "speak_audio" in calls, "wind_url path not exercised"
check("AvatarState enter()/exit() + wind_url (stub robot)", t_avatar_state)


def t_render_and_serve():
    # the exact path say_avatar uses: render a deep-voice WAV, then serve it over HTTP.
    d = tempfile.mkdtemp(prefix="aang_fx_")
    try:
        out = voicefx.render("We are the Avatar.", d, "rage")
    except Exception as e:
        m = repr(e).lower()
        if any(k in m for k in ("getaddrinfo", "timed out", "connection", "ssl",
                                "network", "temporarily", "resolve")):
            raise Skip(f"no network to Edge TTS: {e}")
        raise
    assert os.path.exists(out) and os.path.getsize(out) > 1000, out
    srv = LanAudioServer(d, host="127.0.0.1", port=8127); srv.start()
    with urllib.request.urlopen(srv.url_for("rage.wav", bust=1), timeout=5) as r:
        served = len(r.read())
    srv.stop()
    assert served == os.path.getsize(out), (served, os.path.getsize(out))
check("render deep voice + serve it (say_avatar path)", t_render_and_serve)


print("\n==== SUMMARY ====")
for status, name, detail in results:
    print(f"{status}  {name}" + (f"   ({detail})" if detail and status != "PASS" else ""))
n_fail = sum(1 for r in results if r[0] == "FAIL")
print(f"\n{sum(1 for r in results if r[0]=='PASS')} passed, {n_fail} failed, "
      f"{sum(1 for r in results if r[0]=='SKIP')} skipped")
sys.exit(1 if n_fail else 0)
