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
    # face_id must be one of the robot's installed faces (see tools/probe.py).
    # "adult - Aang3" is the everyday face; "adult - Aang3Avatar" is the glowing Avatar-State
    # variant (build + install both via tools/import_aang_face.py).
    face_id: str = _env("AANG_FACE", "adult - Aang4")
    face_id_avatar: str = _env("AANG_FACE_AVATAR", "adult - Aang4Avatar")

    # ---- Voices (exact voice_id strings confirmed installed on this robot) ----
    voice_normal: str = _env("AANG_VOICE", "Justin-Neural (en-US) - Amazon Polly")
    voice_avatar: str = _env("AANG_VOICE_AVATAR", "ChristopherNeural (en-US) - Microsoft Azure")
    volume: int = int(_env("AANG_VOLUME", "60"))
    volume_avatar: int = int(_env("AANG_VOLUME_AVATAR", "72"))  # a touch louder while enraged (not blasting)

    # ---- Brain (LLM) ----
    brain_provider: str = _env("AANG_BRAIN", "groq")  # groq | anthropic | none
    groq_model: str = _env("AANG_MODEL", "llama-3.3-70b-versatile")
    anthropic_model: str = _env("AANG_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    max_history_turns: int = int(_env("AANG_HISTORY", "12"))

    # ---- Controls (console hotkeys) ----
    hotkey_avatar: str = _env("AANG_HOTKEY_AVATAR", "a").lower()
    hotkey_quit: str = _env("AANG_HOTKEY_QUIT", "q").lower()

    # ---- Avatar State ----
    # The Avatar State burns out on its own after this many seconds (never stays forever).
    # Kept short so he doesn't overstay the rage; he also calms instantly when the LLM tags [CALM].
    avatar_timeout: float = float(_env("AANG_AVATAR_TIMEOUT", "25"))

    # ---- Avatar State wind SFX (served from this PC to the robot) ----
    sfx_enabled: bool = _env("AANG_SFX", "1") == "1"
    sfx_host: str = _env("AANG_SFX_HOST", "")         # autodetected if blank
    sfx_port: int = int(_env("AANG_SFX_PORT", "8077"))
