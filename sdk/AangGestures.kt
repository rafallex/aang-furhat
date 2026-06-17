package furhatos.app.aang.gestures

/*
 * Custom KEYFRAMED gestures — the thing the Realtime API cannot do.
 *
 * In the Furhat SDK a gesture is a timeline of frames. Each frame can:
 *   - drive any face parameter:  PARAM to value      (BasicParams / ARKitParams / CharParams)
 *   - swap the texture/character: texture("..") / character("..")
 *   - set the LED ring:           led(Pixel(r,g,b))
 *   - play a sound:               audio("..")
 * ...and they all animate/interpolate over the frame's time window.
 *
 * API verified against furhat-commons-2.9.2 (defineGesture / frame / reset / FrameBuilder).
 * Use from a flow with:  furhat.gesture(AvatarStateSurge)
 */

import furhatos.gestures.BasicParams
import furhatos.gestures.CharParams
import furhatos.gestures.defineGesture
import furhatos.records.Pixel

/** The Avatar State igniting: eyes flare wide, brows lift, gaze rises, the ring
 *  blazes from black to white — all choreographed in one gesture. */
val AvatarStateSurge = defineGesture("AvatarStateSurge", duration = 3.0) {
    frame(0.0, 0.35) {
        BasicParams.SURPRISE to 0.35
        CharParams.EYES_SCALE_UP to 0.5
        led(Pixel(0, 0, 0))
    }
    frame(0.35, 1.1) {
        BasicParams.SURPRISE to 1.0
        BasicParams.BROW_UP_LEFT to 1.0
        BasicParams.BROW_UP_RIGHT to 1.0
        CharParams.EYES_SCALE_UP to 1.0
        BasicParams.LOOK_UP to 1.0          // gaze to the sky
        led(Pixel(150, 225, 255))
        // audio("avatar_wind.wav")          // drop a wav in src/main/resources to enable
    }
    // Hold the glowing, unblinking stare. persist = keep it until reset/next gesture.
    frame(1.1, 3.0, persist = true) {
        BasicParams.SURPRISE to 0.85
        CharParams.EYES_SCALE_UP to 1.0
        led(Pixel(255, 255, 255))
        // character("Aang Avatar")          // swap to a glowing-arrow character variant if built
    }
}

/** Let the Avatar State go — features relax, ring fades to airbender blue. */
val AvatarStateRelease = defineGesture("AvatarStateRelease", duration = 1.8) {
    frame(0.0, 1.3) {
        BasicParams.SURPRISE to 0.0
        BasicParams.BROW_UP_LEFT to 0.0
        BasicParams.BROW_UP_RIGHT to 0.0
        CharParams.EYES_SCALE_UP to 0.0
        BasicParams.LOOK_UP to 0.0
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
