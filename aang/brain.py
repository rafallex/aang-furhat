"""The conversational brain. Turns recognized speech into an in-character reply,
AND decides — each turn — whether the moment warrants the Avatar State.

The model is instructed (see persona.py) to begin every reply with a control tag,
[CALM] or [AVATAR]. respond() parses that tag, strips it from the spoken text, and
returns (want_avatar, text). The caller drives the transition.

Provider is pluggable:
  - "groq"      -> Groq's free OpenAI-compatible chat API (default)
  - "anthropic" -> Anthropic Messages API
  - "none"      -> deterministic in-character fallbacks (no key needed)
"""

import os
import re
import random
import logging

import requests

from .persona import SYSTEM_NORMAL, SYSTEM_AVATAR, FALLBACKS

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"\[\s*(avatar|calm)\s*\]", re.IGNORECASE)


class Brain:
    def __init__(self, cfg):
        self.cfg = cfg
        self.history = []  # [{"role": "user"|"assistant", "content": str}, ...]
        self.groq_key = os.environ.get("GROQ_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

        self.provider = cfg.brain_provider
        self._fail_count = 0           # consecutive live-call failures
        if self.provider == "groq" and not self.groq_key:
            self.provider = "none"
        elif self.provider == "anthropic" and not self.anthropic_key:
            self.provider = "none"

    # ------------------------------------------------------------------ public
    def describe(self):
        if self.provider == "groq":
            return f"groq ({self.cfg.groq_model})"
        if self.provider == "anthropic":
            return f"anthropic ({self.cfg.anthropic_model})"
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
            elif self.provider == "anthropic":
                raw = self._anthropic(system)
            else:
                raw = random.choice(FALLBACKS)
            self._fail_count = 0
        except Exception as e:
            self._note_failure(e)
            raw = random.choice(FALLBACKS)

        want_avatar, text = self._parse(raw or "", avatar)
        self.history.append({"role": "assistant", "content": text})
        return want_avatar, text

    def _note_failure(self, e):
        """React to a failed live LLM call. An auth error (bad/expired key) is permanent, so
        disable the live brain immediately and warn ONCE -- otherwise every turn silently hits
        the dead endpoint and returns canned lines while the robot looks fine. Transient errors
        (timeout / 429 / 5xx) only disable after a few in a row, so one network blip doesn't
        kill the brain for the session."""
        self._fail_count += 1
        resp = getattr(e, "response", None)
        status = getattr(resp, "status_code", None)
        key_env = "GROQ_API_KEY" if self.cfg.brain_provider == "groq" else "ANTHROPIC_API_KEY"
        if status in (401, 403):
            log.error("LLM auth rejected (HTTP %s) -- disabling live brain, using canned lines "
                      "for the rest of the session. Check %s.", status, key_env)
            self.provider = "none"
        elif self._fail_count >= 3:
            log.error("LLM failed %d turns in a row (last: %s) -- disabling live brain, using "
                      "canned lines. Check connectivity / %s.", self._fail_count, e, key_env)
            self.provider = "none"
        else:
            log.warning("LLM call failed (%s) [%d/3]; canned fallback this turn.",
                        e, self._fail_count)

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

    def _anthropic(self, system):
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.cfg.anthropic_model,
                "system": system,
                "messages": self.history,
                "max_tokens": 200,
                "temperature": 0.85,
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return "".join(block.get("text", "") for block in data.get("content", []))
