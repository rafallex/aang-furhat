# Going deeper than the Realtime API — the Furhat SDK (Kotlin)

The Realtime API is a *remote control*. The **SDK** lets you write skills in Kotlin
that run *on* the robot with the full FaceCore engine — the deepest supported layer:

- **Custom keyframed gestures** — frame-by-frame facial animation, and each frame can
  also swap the **texture/character**, set the **LED**, and play **audio**. (Realtime
  API can't do any of this — it only fires *named* built-in gestures.)
- **Custom characters / masks / textures** loaded as assets.
- **On-robot skills** with the full flow/state-machine, NLU, users, and sensors.

## Your setup status
| Need | Status |
|---|---|
| Furhat SDK | ✅ `2.9.2` at `C:\Users\Rafallex\.furhat\launcher\SDK\2.9.2` |
| JDK 8 (required) | ✅ bundled: `…\.furhat\launcher\JDK\jdk8u265-b01` |
| Gradle | ✅ via each skill's `gradlew` wrapper (no global install needed) |
| Editor | ⚠️ you have **PyCharm**, not IntelliJ IDEA. Skills build from the CLI with `gradlew`, so that's fine — but for editing Kotlin with autocomplete, install **IntelliJ IDEA Community** (free). |

## 1. Create the skill skeleton
**Easiest:** open the **Furhat SDK launcher** app → **New Skill** → name it `Aang`
→ choose this `sdk/` folder. It generates a correct project (package `furhatos.app.aang`).

**Or via CLI:**
```powershell
cd C:\Users\Rafallex\.furhat\launcher\SDK\2.9.2
.\gradlew createSkill --name=Aang --folder=C:\Users\Rafallex\Documents\Furhat-Internship\Avatar\sdk
```

## 2. Drop in the Aang code
Copy [AangGestures.kt](sdk/AangGestures.kt) into the generated skill at
`src/main/kotlin/furhatos/app/aang/gestures/AangGestures.kt`.

Then wire it into a flow state (e.g. `flow/main/`). Minimal integration:

```kotlin
import furhatos.app.aang.gestures.*
import furhatos.flow.kotlin.*
import furhatos.flow.kotlin.voice.Voice

val AangMain: State = state {
    onEntry {
        furhat.setCharacter("Aang")                       // your imported face (or set it in Furhat Studio)
        furhat.setVoice(Voice(name = "Justin-Neural"))    // young Aang
        furhat.ledStrip.solid(java.awt.Color(42, 107, 192))
        furhat.gesture(PlayfulGrin)
        furhat.ask("Hi! I'm Aang. What do you want to know?")
    }
    onResponse {
        val text = it.text.lowercase()
        if ("avatar state" in text || "the world needs the avatar" in text) {
            furhat.setVoice(Voice(name = "Matthew-Neural"))  // deep, booming
            furhat.gesture(AvatarStateSurge)
            furhat.say("We are the bridge between worlds. Every Avatar before us speaks as one.")
        } else {
            // hand off to your LLM here, then:
            furhat.say("Hmm, let me think about that.")
            reentry()
        }
    }
}
```

## 3. Build the `.skill`
```powershell
cd <your Aang skill folder>
.\gradlew shadowJar      # produces build\libs\aang.skill
```

## 4. Run it
- **On the Virtual Furhat** (dev): start Virtual Furhat from the SDK launcher, then run the
  skill (`.\gradlew run`, or the green ▶ next to `main()` in IntelliJ).
- **On the real robot**: open **Furhat Studio** (`http://192.168.1.107/`) → **Skills** →
  upload `aang.skill` and run it there.

## Notes
- A few flow setters (`setCharacter`, exact `Voice` args) vary slightly by version — let
  IntelliJ autocomplete confirm them. The **gesture file is verified** against 2.9.2.
- This complements the Python Realtime app in the parent folder; pick the SDK when you need
  custom gestures / characters / on-robot logic, and Realtime for quick remote control.
