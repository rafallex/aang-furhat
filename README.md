# Aang on Furhat — a conversational Avatar with an unlockable Avatar State

Aang (from *Avatar: The Last Airbender*) built as a real, talking character on a
**Furhat** social robot, driven entirely over the **Furhat Realtime API** (the
WebSocket API on port `9000`). Talk to him like the playful twelve-year-old
Air Nomad he is — and when the moment calls for it, **unlock the Avatar State**:
the head rises, the ring blazes white, the wind rushes in, and the voice of a
thousand past lives speaks through him.

## What it does

- **Full conversation** — speech recognition → LLM → speech, in character, over the
  Realtime API (`request.listen.*` → brain → `request.speak.text`).
- **The Avatar State** — a choreographed transformation: frozen unblinking stare,
  a breathing white/cyan LED surge, a slow head-rise, a swap to a deep booming
  voice, a wind whoosh, and a different LLM persona (the chorus of all past Avatars).
- **Two ways to unlock it** — a spoken trigger phrase *or* a keyboard hotkey, so it's
  magical when you want it and reliable when you're demoing.

## The look (honest scope)

The Furhat projects a *texture* onto a physical mask. The Realtime API can only
**select** an installed face — it can't paint a new one. So out of the box Aang
wears the closest stock face to a 12-year-old (`child - Billy`), and the
"Aang-ness" comes from persona, voice, and the Avatar State FX.

A true Aang look — **bald head + blue arrow tattoo**, with the eyes/arrows glowing
in the Avatar State — needs a **custom face texture** built with the Furhat SDK /
FaceCore character pipeline (the same path that produced the custom `adult - Jules`
face on this robot). That's the planned next step; see *Roadmap* below.

## Setup

```powershell
pip install -r requirements.txt

# free LLM key (no credit card): https://console.groq.com/keys
setx GROQ_API_KEY "gsk_..."      # restart the shell after setx
```

No key? Aang still runs and performs — he just falls back to a few canned lines
instead of free conversation.

## Run

```powershell
python aang_app.py
```

```
Controls:  [a] toggle the Avatar State    [q] quit
```

Speech triggers:

| Say… | Effect |
|---|---|
| *(no phrase — the conversation turns dire)* | **Aang surges into the Avatar State on his own** — the LLM judges the stakes each turn |
| "the world needs the avatar" / "avatar state" / "go avatar" | manually enter the Avatar State |
| "come back Aang" / "calm down" / "that's enough" | leave the Avatar State |
| "goodbye Aang" / "shut down" | quit |

## Files

| File | What it is |
|---|---|
| `aang_app.py` | The show: conversation loop, hotkeys, trigger phrases. |
| `aang/furhat.py` | Synchronous Furhat **Realtime API** client (WebSocket + helpers). |
| `aang/persona.py` | Aang's two system prompts (young monk / Avatar State) and all his lines. |
| `aang/brain.py` | Pluggable LLM brain — Groq (default), Anthropic, or canned fallback. |
| `aang/avatar_state.py` | The Avatar State choreography (LED glow, head-rise, voice swap, wind). |
| `aang/sfx.py` | Generates the wind whoosh WAV and serves it to the robot over HTTP. |
| `aang/config.py` | All settings, each overridable by an environment variable. |
| `tools/probe.py` | Lists the robot's installed faces and voices (how `child - Billy` etc. were chosen). |
| `tools/smoke_test.py` | One-shot hardware check of every primitive Aang uses. |

## How to tweak

Everything is an env var (see `.env.example`) — no code edits needed:

- **Different face/voice?** Run `python tools/probe.py en-US` to list options, then set
  `AANG_FACE` / `AANG_VOICE` / `AANG_VOICE_AVATAR`.
- **Different robot?** Set `FURHAT_HOST`.
- **Different brain?** `AANG_BRAIN=anthropic` (+ `ANTHROPIC_API_KEY`), or `AANG_MODEL=...`.
- **Head looks down instead of up in the Avatar State?** Flip `LOOK_UP_PITCH` in
  `aang/avatar_state.py` (the sign convention varies by unit).

## The blue arrow — a custom FaceCore character (`face/`)

The Realtime API can only *select* a face, not paint one. And Furhat's character
*import* only re-combines existing library textures — it can't introduce a new marking.
So the arrow is **baked into a custom skin texture** and installed as an **asset pack**,
which only loads after a **robot restart**. `face/build_aang_face.py` builds `face/Aang.zip`
from the Jules export (same adult-mask UV): it lightens the skin, paints the blue arrow
onto the forehead (UV-aligned), and removes the goatee.

To install it (the recipe that actually works):

```powershell
python face/build_aang_face.py            # arrow baked into skin -> face/Aang.zip
python tools/import_aang_face.py deploy    # POST /assetpack/deploy (overwrite)
#  >>> RESTART THE ROBOT <<<               # FaceCore loads asset packs on boot
python tools/import_aang_face.py select    # face.config -> "adult - Aang"
```

Tweaking the arrow (color/size/position) means: edit the constants atop
`face/build_aang_face.py`, rebuild, redeploy, **restart**, select. (Restarts are the slow
part — get placement right in as few as possible.)

### Still to do
- An **Avatar-State variant** with a white/glowing arrow, swapped in by
  `avatar_state.enter()/exit()` via `request.face.config`.
- Optionally rebuild on the **child mask** (rounder, younger) — needs a child-based
  character exported from Studio to get that mask's UV layout.

## Stack

Furhat Realtime API (WebSocket, port 9000) · Python (`websocket-client`) ·
Groq free tier for the brain · numpy for the wind SFX.
