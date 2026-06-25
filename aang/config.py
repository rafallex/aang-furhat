"""Central configuration. Every value can be overridden with an environment
variable so you never have to edit code to point at a different robot, voice,
face, or LLM."""

import os
from dataclasses import dataclass


def _env(name, default):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


@dataclass
class Config:
    # ---- Robot (Furhat Realtime API) ----
    host: str = _env("FURHAT_HOST", "192.168.1.107")
    port: int = int(_env("FURHAT_PORT", "9000"))
    auth_key: str = _env("FURHAT_KEY", None)          # only if your robot requires one

    # ---- Look ----
    # face_id must be one of the robot's installed faces.
    # "adult - Aang4" is the everyday face; "adult - Aang4Avatar" is the glowing Avatar-State
    # variant (build both with face/build_aang_face.py).
    face_id: str = _env("AANG_FACE", "adult - Aang4")
    face_id_avatar: str = _env("AANG_FACE_AVATAR", "adult - Aang4Avatar")

    # ---- Voices (exact voice_id strings confirmed installed on this robot) ----
    voice_normal: str = _env("AANG_VOICE", "Justin-Neural (en-US) - Amazon Polly")
    # NOTE: voice_avatar is the robot's NATIVE deep voice, used only as the FALLBACK --
    # when AANG_AVATAR_FX=0, or if a deep-voice render/playback fails mid-line. The normal
    # rendered Avatar voice uses the edge-tts voice AANG_FX_VOICE (in avatar_voice_fx.py),
    # so changing AANG_VOICE_AVATAR has no effect while the FX voice is working.
    voice_avatar: str = _env("AANG_VOICE_AVATAR", "ChristopherNeural (en-US) - Microsoft Azure")
    volume: int = int(_env("AANG_VOLUME", "60"))
    volume_avatar: int = int(_env("AANG_VOLUME_AVATAR", "72"))  # a touch louder while enraged (not blasting)

    # Avatar-State voice: render a deep-voice FX file (1, default) or use the robot's
    # plain deep native voice (0). FX needs the robot to fetch the audio from this PC (Ethernet).
    avatar_voice_fx: bool = _env("AANG_AVATAR_FX", "1") == "1"

    # ---- Brain (LLM) ----
    brain_provider: str = _env("AANG_BRAIN", "groq")  # groq | none
    groq_model: str = _env("AANG_MODEL", "llama-3.3-70b-versatile")
    max_history_turns: int = int(_env("AANG_HISTORY", "12"))

    # ---- Controls (console hotkeys) ----
    hotkey_avatar: str = _env("AANG_HOTKEY_AVATAR", "a").lower()
    hotkey_quit: str = _env("AANG_HOTKEY_QUIT", "q").lower()
    hotkey_talk: str = _env("AANG_HOTKEY_TALK", " ")   # optional push-to-talk key (default: space)

    # Normal hands-free conversation is the DEFAULT (open mic). Push-to-talk is only an
    # optional fallback for a noisy room / if robot-side echo cancellation isn't enough:
    # set AANG_PTT=1 to enable it.
    push_to_talk: bool = _env("AANG_PTT", "0") == "1"

    # ---- Avatar State ----
    # The Avatar State burns out on its own after this many seconds (never stays forever).
    # Kept short so he doesn't overstay the rage; he also calms instantly when the LLM tags [CALM].
    avatar_timeout: float = float(_env("AANG_AVATAR_TIMEOUT", "25"))

    # ---- LAN audio server (this PC serves audio the robot fetches via request.speak.audio) ----
    # ONE server/port now serves BOTH the Avatar-State wind AND the rendered deep voice.
    # (AANG_SFX toggles only the wind; the deep voice is toggled by AANG_AVATAR_FX above.)
    sfx_enabled: bool = _env("AANG_SFX", "1") == "1"    # enable the wind whoosh
    sfx_host: str = _env("AANG_SFX_HOST", "")           # this PC's LAN IP; autodetected if blank
    sfx_port: int = int(_env("AANG_SFX_PORT", "8077"))  # single port for all robot-fetched audio
