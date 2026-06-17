# Aang on Furhat — a conversational Avatar with an unlockable Avatar State

Aang (from *Avatar: The Last Airbender*) built as a real, talking character on a
**Furhat** social robot, driven entirely over the **Furhat Realtime API** (the
WebSocket API on port `9000`). Talk to him like the playful twelve-year-old
Air Nomad he is — and when the moment calls for it, **unlock the Avatar State**:
the head rises, the arrow blazes white, the wind rushes in, and the voice of a
thousand past lives speaks through him.

## What it does

- **Full conversation** — speech recognition → LLM → speech, in character, over the
  Realtime API (`request.listen.*` → brain → `request.speak.*`).
- **A custom Aang face** — a back-projected FaceCore texture with the blue arrow
  tattoo baked onto the forehead, on a warm Mediterranean skin (see *The face* below).
- **The Avatar State** — a choreographed transformation: a face swap to the glowing
  variant (white arrow + solid-white "ghost" eyes), a frozen unblinking glare, a
  breathing white/cyan LED surge, a slow head-rise, a wind whoosh, a different LLM
  persona (the chorus of all past Avatars), and **the chorus voice** — layered,
  detuned copies of the line with light reverb, so it sounds like many voices at once.
- **Three ways in, and it leaves on its own** — the LLM can **surge into the Avatar
  State by itself** when the stakes turn dire, or you can trigger it with a **spoken
  phrase** or a **keyboard hotkey**. It always burns back down — after a timeout, or
  the instant the LLM judges the moment has calmed.

## Setup

```powershell
pip install -r requirements.txt

# free LLM key (no credit card): https://console.groq.com/keys
setx GROQ_API_KEY "gsk_..."      # restart the shell after setx
```

No key? Aang still runs and performs — he just falls back to a few canned lines
instead of free conversation. The Avatar **chorus voice** uses `edge-tts` (neural TTS,
no key) layered with `pydub`; if those aren't available he simply speaks the Avatar
lines in the configured fallback TTS voice instead.

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
| `aang_app.py` | The show: conversation loop, hotkeys, trigger phrases, reconnect handling. |
| `aang/furhat.py` | Synchronous Furhat **Realtime API** client (WebSocket + helpers, audio speak, reconnect). |
| `aang/persona.py` | Aang's two system prompts (young monk / Avatar State) and all his lines. |
| `aang/brain.py` | Pluggable LLM brain — Groq (default), Anthropic, or canned fallback; emits `[CALM]`/`[AVATAR]` tags for self-switching. |
| `aang/avatar_state.py` | The Avatar State choreography (face swap, LED glow, head-rise, glare, wind, auto-return). |
| `aang/avatar_voice_fx.py` | The **chorus voice**: `edge-tts` → layered detuned copies + reverb, served to the robot over HTTP. |
| `aang/sfx.py` | Generates the wind-whoosh WAV and serves it to the robot over HTTP. |
| `aang/config.py` | All settings, each overridable by an environment variable. |
| `face/build_aang_face.py` | Builds the custom face pack `face/Aang.zip` (both faces, baked arrow). |
| `tools/import_aang_face.py` | Installs the face pack on the robot (`deploy` / `select`). |
| `tools/probe.py` | Lists the robot's installed faces and voices. |
| `tools/smoke_test.py` | One-shot hardware check of every primitive Aang uses. |

## How to tweak

Everything is an env var (see `.env.example`) — no code edits needed:

- **Different face/voice?** Run `python tools/probe.py en-US` to list options, then set
  `AANG_FACE` / `AANG_FACE_AVATAR` / `AANG_VOICE` / `AANG_VOICE_AVATAR`.
- **Different robot?** Set `FURHAT_HOST`.
- **Different brain?** `AANG_BRAIN=anthropic` (+ `ANTHROPIC_API_KEY`), or `AANG_MODEL=...`.
- **Avatar State too long / too short?** `AANG_AVATAR_TIMEOUT` (seconds; default 25).
- **Head looks down instead of up in the Avatar State?** Flip `LOOK_UP_PITCH` in
  `aang/avatar_state.py` (the sign convention varies by unit).

## The face — a custom FaceCore character (`face/`)

The Furhat projects a *texture* onto a physical mask, and the Realtime API can only
**select** an installed face — it can't paint one. Furhat's character *import* only
re-combines existing library textures, so it can't introduce a new marking either.
So the arrow is **baked into a custom skin texture** and installed as an **asset pack**.

`face/build_aang_face.py` builds **one** pack (`face/Aang.zip`) holding **two** characters
(asset packs are singular — each deploy replaces the previous, so both must be bundled):

| Face | Skin | Arrow | Eyes |
|---|---|---|---|
| `adult - Aang4` | warm dark Mediterranean | deep blue | blue-grey |
| `adult - Aang4Avatar` | *same* skin | glowing pure-white (with bloom halo) | solid-white "ghost" |

Both faces share the **same** skin — in the show Aang's skin doesn't change, only the
arrow and eyes glow in the Avatar State — so the arrow sits in the **exact same spot** on
both, and the app just swaps faces via `request.face.config` in `avatar_state.enter()/exit()`.
The skin is deliberately dark and warm (the Furhat projector over-brightens and over-warms
colours) so the white arrow and ghost eyes pop hard against it.

To install it:

```powershell
python face/build_aang_face.py             # bake both faces -> face/Aang.zip
python tools/import_aang_face.py deploy     # importCharacter (live) + /assetpack/deploy (textures)
#  >>> RESTART THE ROBOT <<<                 # FaceCore loads asset-pack textures on boot
python tools/import_aang_face.py select     # face.config -> "adult - Aang4"
```

Tweaking the arrow (colour/size/position) or skin **darkness** means: edit the constants
atop `face/build_aang_face.py`, rebuild, redeploy, **restart**, select. (Restarts are the
slow part — get placement right in as few as possible.) The skin **hue** can be nudged
live via the character profile's `tm_skins_c` tint without a restart.

## Prebuilt binary

Don't want to bake the face yourself? The ready-to-install face pack (`Aang.zip`) is
attached to the GitHub [**v1.0** release](https://github.com/rafallex/aang-furhat/releases/tag/v1.0) —
download it and skip straight to `python tools/import_aang_face.py deploy`.

## Stack

Furhat Realtime API (WebSocket, port 9000) · Python (`websocket-client`) ·
Groq free tier for the brain · `edge-tts` + `pydub` for the Avatar chorus voice ·
numpy + PIL for the wind SFX and the baked face texture.
