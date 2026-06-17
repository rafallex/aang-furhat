package furhatos.app.aang.gestures

/*
 * Custom KEYFRAMED gestures — the thing the Realtime API cannot do.
 * Each frame drives face params and can also swap texture/character, set the
 * LED, and play audio, all interpolated over the frame's time window.
 * Verified against furhat-commons 2.9.2.
 */

import furhatos.gestures.BasicParams
import furhatos.gestures.CharParams
import furhatos.gestures.defineGesture
import furhatos.records.Pixel

/** The Avatar State igniting: eyes flare, brows lift, gaze rises, ring goes black to white. */
val AvatarStateSurge = defineGesture("AvatarStateSurge", duration = 3.0) {
    frame(0.0, 0.35) {
        character("Aang4Avatar")              // swap to the GLOWING face
        CharParams.EYES_SCALE_UP to 0.5
        led(Pixel(0, 0, 0))
    }
    frame(0.35, 1.1) {
        BasicParams.EXPR_ANGER to 0.6         // FURY, not serenity
        BasicParams.BROW_DOWN_LEFT to 1.0
        BasicParams.BROW_DOWN_RIGHT to 1.0
        CharParams.EYES_SCALE_UP to 1.0       // eyes wide so the glow shows
        led(Pixel(150, 225, 255))
    }
    frame(1.1, 3.0, persist = true) {
        BasicParams.EXPR_ANGER to 0.6
        BasicParams.BROW_DOWN_LEFT to 1.0
        BasicParams.BROW_DOWN_RIGHT to 1.0
        CharParams.EYES_SCALE_UP to 1.0
        led(Pixel(255, 255, 255))
    }
}

/** Release the Avatar State: features relax, ring fades to airbender blue. */
val AvatarStateRelease = defineGesture("AvatarStateRelease", duration = 1.8) {
    frame(0.0, 1.3) {
        character("Aang4")                    // back to the everyday face
        BasicParams.EXPR_ANGER to 0.0
        BasicParams.BROW_DOWN_LEFT to 0.0
        BasicParams.BROW_DOWN_RIGHT to 0.0
        CharParams.EYES_SCALE_UP to 0.0
        led(Pixel(42, 107, 192))
    }
    reset(1.8)
}

/** A playful, twelve-year-old grin. */
val PlayfulGrin = defineGesture("PlayfulGrin", duration = 1.6) {
    frame(0.0, 0.3) {
        BasicParams.SMILE_OPEN to 0.4
        BasicParams.BROW_UP_LEFT to 0.3
        BasicParams.BROW_UP_RIGHT to 0.3
    }
    frame(0.3, 1.2) {
        BasicParams.SMILE_OPEN to 1.0
        BasicParams.EYE_SQUINT_LEFT to 0.3
        BasicParams.EYE_SQUINT_RIGHT to 0.3
    }
    reset(1.6)
}

/** Meditative airbender calm: eyes close, a slow settling breath. */
val MeditativeCalm = defineGesture("MeditativeCalm", duration = 3.0) {
    frame(0.0, 1.0) {
        BasicParams.BLINK_LEFT to 1.0
        BasicParams.BLINK_RIGHT to 1.0
        BasicParams.SMILE_CLOSED to 0.3
    }
    frame(1.0, 2.4, persist = true) {
        BasicParams.BLINK_LEFT to 1.0
        BasicParams.BLINK_RIGHT to 1.0
    }
    reset(3.0)
}
