# Aang on Furhat — speaker notes

_9-slide technical deep-dive. ~3-min lightning talk._

## 1. Title

Aang from Avatar: The Last Airbender, built as a real talking character on a Furhat social robot — driven entirely over the Furhat Realtime API. Today: how the conversation loop works, how the LLM flips its own persona, and the choreographed Avatar State it surges into.

## 2. Realtime API

The whole thing rides one WebSocket on port 9000. Every message is JSON tagged with a type — request dot something going out, response dot something coming back. A background reader thread parses everything into a queue; the main thread drives the robot and blocks on wait_for when it needs a specific reply, like end-of-speech.

## 3. Conversation loop

The conversation is three stages on a loop. Listen returns recognized text. The brain turns that text into a reply. Speak says it back and blocks until end-of-speech. Then straight back to listen. That's the whole heartbeat.

## 4. Self-switching brain

This is the trick I'm proudest of. The model is told to begin every reply with a control tag — bracket CALM or bracket AVATAR. respond() reads that tag, strips it out of the spoken text, and returns a boolean plus the clean line. No tag means keep the current state. So the LLM decides, turn by turn, whether the stakes are dire enough to surge — alongside a spoken phrase or a hotkey. And it always burns back down.

## 5. Avatar State

And here's the payoff. When that AVATAR verdict comes back, a whole choreography fires: swap to the glowing face, freeze the eyes into an unblinking glare, surge the LED ring from black up to a breathing white, rise the head to the sky, whoosh the wind, and switch to the chorus voice — the line layered with detuned copies of itself and a touch of reverb, so it sounds like a thousand past lives speaking at once.

## 6. Chorus voice

The Avatar lines don't come from the robot's own text-to-speech. A neural voice renders the line off-board, then it's layered with detuned copies of itself plus a little reverb — so one line sounds like a thousand voices speaking as one. That audio is served over HTTP and played back with lip-sync. No edge-tts? It quietly falls back to plain TTS.

## 7. Custom face

One catch: the Realtime API can only select an installed face — it can't paint a new marking. So the arrow is baked straight into a custom skin texture and shipped as an asset pack. The pack holds two characters on the same skin — the everyday blue arrow, and the glowing white version with ghost eyes. The app just swaps between them with face.config.

## 8. Resilience

Two things make this survive a live demo. First, the WebSocket drops sometimes — a robot blip, an idle close. A background reader flips a flag, the main loop notices, reconnects, re-authenticates, resets the Avatar State, and re-dresses the robot from scratch: voice, face, LEDs, listen config. Second, no API keys? It still runs — canned in-character lines instead of a live brain, and plain TTS instead of the chorus. The show never stops.

## 9. Stack

That's the whole thing: one WebSocket, a brain that tags its own state, and a choreographed surge with a layered chorus voice — running on a free stack. Everything is an env var, so there's nothing to edit to retune it. May the spirits watch over you.
