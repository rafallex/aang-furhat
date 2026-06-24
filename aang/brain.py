"""The conversational brain. Turns recognized speech into an in-character reply,
AND decides — each turn — whether the moment warrants the Avatar State.

The model is instructed (see persona.py) to begin every reply with a control tag,
[CALM] or [AVATAR]. respond() parses that tag, strips it from the spoken text, and
returns (want_avatar, text). The caller drives the transition.

Provider is pluggable:
  - "groq"      -> Groq's free OpenAI-compatible chat API (default)
  - "none"      -> deterministic in-character fallbacks (no key needed)
"""

import os
import re
import random

import requests

from .persona import SYSTEM_NORMAL, SYSTEM_AVATAR, FALLBACKS

_TAG_RE = re.compile(r"\[\s*(avatar|calm)\s*\]", re.IGNORECASE)


class Brain:
    def __init__(self, cfg):
        self.cfg = cfg
        self.history = []  # [{"role": "user"|"assistant", "content": str}, ...]
        self.groq_key = os.environ.get("GROQ_API_KEY")

        self.provider = cfg.brain_provider
        if self.provider == "groq" and not self.groq_key:
            self.provider = "none"

    # ------------------------------------------------------------------ public
    def describe(self):
        if self.provider == "groq":
            return f"groq ({self.cfg.groq_model})"
        return "none (canned fallback lines)"

    def reset(self):
        self.history = []

    def respond(self, user_text, avatar=False):
        """Return (want_avatar: bool, text: str)."""
        system = SYSTEM_AVATAR if avatar else SYSTEM_NORMAL
        self.history.append({"role": "user", "content": user_text})
        self._trim()
        try:
            if self.provider == "groq":
                raw = self._groq(system)
            else:
                raw = random.choice(FALLBACKS)
        except Exception as e:
            print(f"[brain] {self.provider} call failed ({e}); using fallback.")
            raw = random.choice(FALLBACKS)

        want_avatar, text = self._parse(raw or "", avatar)
        self.history.append({"role": "assistant", "content": text})
        return want_avatar, text

    # ------------------------------------------------------------------ internals
    @staticmethod
    def _parse(raw, current):
        """Read the [CALM]/[AVATAR] tag (no tag -> keep current), strip it out."""
        tags = [m.group(1).lower() for m in _TAG_RE.finditer(raw)]
        if "avatar" in tags:
            want = True
        elif "calm" in tags:
            want = False
        else:
            want = current
        text = _TAG_RE.sub("", raw).strip()
        return want, (text or random.choice(FALLBACKS))

    def _trim(self):
        cap = self.cfg.max_history_turns * 2
        if len(self.history) > cap:
            self.history = self.history[-cap:]

    def _groq(self, system):
        messages = [{"role": "system", "content": system}] + self.history
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.groq_key}"},
            json={
                "model": self.cfg.groq_model,
                "messages": messages,
                "temperature": 0.85,
                "max_tokens": 160,
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
