# Aang on Furhat — speaker notes

_9-slide technical deep-dive. ~3-min lightning talk._

## 1. Title

This is what I built during my internship: Aang, from Avatar: The Last Airbender, as a fully working character on a real Furhat robot. He holds a real conversation in character — and when the moment turns dire, he transforms into the Avatar State entirely on his own. I'll walk through what it does, the two pieces I'm proudest of, and where it could go next.

## 2. What I built

At a glance: a complete, working character. He turns toward whoever's speaking, greets them, and holds a genuine back-and-forth in character. He decides on his own when the stakes are high enough to transform. He has a custom face and a layered voice I built from scratch. And he recovers from problems without being babysat. Under the hood it's simple to describe — he listens, thinks, and speaks on a loop. Nothing is installed on the robot itself; my code drives it live over the network.

## 3. The brain decides

This is the piece I'm proudest of. There's no keyword and no button. Every single turn, the language model weighs the conversation and decides for itself whether the stakes are high enough to transform — and when things calm down, it lets go on its own. Technically: every reply carries a hidden cue that tells the system to stay calm or to surge, and I read that and drive the transformation. To be precise about what it is — it's a text language model, Groq running Llama 3.3 70B, reading the words from the robot's speech recognition. It does not see; the camera is only used so Aang turns toward whoever's talking.

## 4. Avatar State

And here's the payoff. The instant that verdict says surge, one trigger fires a whole performance: his face transforms to the glowing version, his eyes lock into an unblinking stare, the light ring surges up and starts breathing, his head rises to the sky, and the wind rushes in. It's choreographed to feel like the show.

## 5. Chorus voice

The detail that really sells it is the voice. In the Avatar State, Aang doesn't use the robot's normal text-to-speech. Each line is rendered by a neural voice, then layered with slightly detuned copies of itself plus a touch of reverb — so one line sounds like a thousand past lives speaking as one. It's built fresh for every line and played back in sync.

## 6. Custom face

The look was its own challenge. Furhat projects a face onto a physical mask, and the system can only pick from faces that are already installed — it can't draw a new marking like Aang's arrow. So I baked the tattoo straight into the projector's skin texture and shipped two versions of him on the same skin: the everyday blue arrow, and the glowing white one with ghost eyes. The app just swaps between them live as he transforms.
