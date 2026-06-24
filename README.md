# Aang on Furhat — a conversational Avatar with an unlockable Avatar State

Aang (from *Avatar: The Last Airbender*) built as a real, talking character on a
**Furhat** social robot, driven entirely over the **Furhat Realtime API** (the
WebSocket API on port `9000`). Talk to him like the playful twelve-year-old
Air Nomad he is — and when the moment calls for it, **unlock the Avatar State**:
the head rises, the arrow blazes white, the wind rushes in, and a single deep,
otherworldly voice speaks through him.

**Nothing is installed on the robot** — Python (`aang_app.py`) drives it live over
the Realtime API.

## What it does

- **Hands-free conversation** — open-mic speech recognition → LLM → speech, in
  character, over the Realtime API (`request.listen.*` → brain → `request.speak.*`).
  No push-to-talk by default; a **self-echo filter** stops him replying to himself.
  The camera is used **only to turn him toward the speaker** — there is no vision.
- **A custom Aang face** — a back-projected FaceCore texture with the blue arrow
  tattoo baked onto the forehead, on a warm Mediterranean skin (see *The face* below).
  A **per-turn face self-heal** re-asserts his face so the robot never reverts.
- **The Avatar State** — a choreographed transformation: a face swap to the glowing
  variant (white arrow + solid-white "ghost" eyes), a frozen unblinking glare, a
  breathing white/cyan LED surge, a slow head-rise, a wind whoosh, a different LLM
  persona (the voice of all past Avatars), and **a single deep voice** — each
  Avatar-State line is re-synthesized with the neural TTS engine's pitch dropped
  well below normal (~-30Hz), **dry: no reverb, no layered/detuned "chorus" copies**.
  (The original "chorus of past lives" idea — layered detuned copies plus reverb —
  was tried and **dropped**: it doubled and sounded muddy on the robot's own speaker.)
- **It surges in on its own, and leaves on its own** — primarily, the **text LLM
  reads the recognized speech each turn and self-triggers** the Avatar State (tagging
  `[CALM]`/`[AVATAR]`) when the stakes turn dire — **no keyword, no button**. Spoken
  trigger phrases and the `[a]` hotkey are only optional **manual overrides**. It
  always burns back down — after a timeout, or the instant the LLM judges the moment
  has calmed.

## Prerequisites

- **Stop any running Furhat AI Creator skill first** — it fights the Realtime-API app
  (both want the robot's voice/listen pipeline). Stop it before launching the demo.
- **Run on Ethernet.** WiFi was unstable in testing, and the robot must reach this PC
  over the LAN to fetch the rendered voice and wind-SFX WAVs over HTTP. Two local HTTP
  ports must be reachable from the robot: **8079** (deep-voice WAVs, `AANG_FX_PORT`) and
  **8077** (wind SFX, `AANG_SFX_PORT`) — open both if a firewall is in the way.

## Setup

```powershell
# (optional but recommended) create the conda env the Run step activates
conda create -n furhat python=3.11 -y
conda activate furhat

pip install -r requirements.txt

# point at the robot (its IP on the LAN)
setx FURHAT_HOST "192.168.1.107"   # restart the shell after setx

# free LLM key (no credit card): https://console.groq.com/keys
setx GROQ_API_KEY "gsk_..."        # restart the shell after setx
```

No key? Aang still runs and performs — he just falls back to a few canned lines
instead of free conversation. The Avatar **deep voice** is rendered with `edge-tts`
(neural TTS, no key) processed by `pydub`; if rendering fails or `AANG_AVATAR_FX=0`,
he falls back to the robot's **native deep voice** (`AANG_VOICE_AVATAR`) instead.

## Run

```powershell
conda activate furhat
$env:FURHAT_HOST = "192.168.1.107"   # the robot's IP, if not already set
python -u aang_app.py
```

```
Controls:  [a] toggle the Avatar State    [q] quit
```

The console hotkey loop is **Windows-only** (it uses `msvcrt`); on other platforms the
keys are simply inactive and Aang runs hands-free off speech alone.

The Avatar State is normally **driven by the LLM itself** — it reads each turn and
surges in/out on its own (see *What it does*). The phrases and `[a]` hotkey below are
only optional **manual overrides**:

| Say… | Effect |
|---|---|
| *(no phrase — the conversation turns dire)* | **Aang surges into the Avatar State on his own** — the LLM judges the stakes each turn (primary path) |
| "the world needs the avatar" / "avatar state" / "go avatar" | manually enter the Avatar State (override) |
| "come back Aang" / "calm down" / "that's enough" | leave the Avatar State (override) |
| "goodbye Aang" / "shut down" | quit |

## Files

| File | What it is |
|---|---|
| `aang_app.py` | The show: hands-free conversation loop, self-echo filter, per-turn face self-heal, hotkeys, trigger phrases, ~2-min reconnect retry. |
| `aang/furhat.py` | Synchronous Furhat **Realtime API** client (WebSocket + helpers, audio speak, reconnect). |
| `aang/persona.py` | Aang's two system prompts (young monk / Avatar State) and all his lines. |
| `aang/brain.py` | Pluggable LLM brain — Groq (default), Anthropic, or canned fallback; emits `[CALM]`/`[AVATAR]` tags for self-switching. |
| `aang/avatar_state.py` | The Avatar State choreography (face swap, LED glow, head-rise, glare, wind, auto-return). |
| `aang/avatar_voice_fx.py` | The **deep voice**: `edge-tts` rendered with the engine's pitch dropped (~-30Hz), dry — no reverb, no layered copies — served to the robot over HTTP. |
| `aang/sfx.py` | Generates the wind-whoosh WAV and serves it to the robot over HTTP. |
| `aang/config.py` | All settings, each overridable by an environment variable. |
| `face/build_aang_face.py` | Builds the custom face pack `face/Aang.zip` (both faces, baked arrow). |
| `tools/import_aang_face.py` | Installs the face pack on the robot (`deploy` / `select`). |
| `tools/probe.py` | Lists the robot's installed faces and voices. |
| `tools/smoke_test.py` | One-shot hardware check of every primitive Aang uses. |
| `tools/avatar_demo.py` | One-shot Avatar-State showpiece (no mic/conversation) — for filming the transformation. |
| `tools/face_console.py` | Interactive console to drive the face / LED / head params live (diagnostics + tuning). |

## How to tweak

Everything is an env var (see `.env.example`) — no code edits needed:

- **Different face/voice?** Run `python tools/probe.py en-US` to list options, then set
  `AANG_FACE` / `AANG_FACE_AVATAR` / `AANG_VOICE` / `AANG_VOICE_AVATAR`.
- **Different robot?** Set `FURHAT_HOST`.
- **Different brain?** `AANG_BRAIN=anthropic` (+ `ANTHROPIC_API_KEY`), or `AANG_MODEL=...`.
- **Deep Avatar voice on/off?** `AANG_AVATAR_FX=1` (default) renders the deep voice from
  this PC; `AANG_AVATAR_FX=0` uses the robot's native deep voice (`AANG_VOICE_AVATAR`).
  Pick the edge-tts voice with `AANG_FX_VOICE` (default `en-US-ChristopherNeural`). The
  rendered WAVs are served on `AANG_FX_PORT` (default `8079`, must be LAN-reachable) and
  written to `AANG_FX_DIR` (default `%TEMP%\aang_fx`).
- **Push-to-talk instead of open mic?** `AANG_PTT=1` enables push-to-talk (hold the
  space key); the default `AANG_PTT=0` is hands-free open mic.
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
python tools/import_aang_face.py deploy     # /assetpack/deploy -> textures + profiles
#  >>> RESTART THE ROBOT <<<                 # FaceCore loads asset-pack textures on boot
python tools/import_aang_face.py select     # face.config -> "adult - Aang4"
```

> `AANG_CHAR_NAME` (default `Aang4`) sets the character name the pack installs/selects as.

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
Groq free tier (Llama 3.3 70B) for the brain · `edge-tts` + `pydub` for the Avatar
deep voice · numpy + PIL for the wind SFX and the baked face texture.

## License

MIT — see [LICENSE](LICENSE). This is a non-commercial, educational **fan project**:
*Avatar: The Last Airbender*, Aang, and related names and likenesses belong to their
respective rights holders (Nickelodeon / Paramount), and this project is not affiliated
with or endorsed by them.
