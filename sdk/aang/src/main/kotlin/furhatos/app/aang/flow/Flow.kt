package furhatos.app.aang.flow

import furhatos.app.aang.Brain
import furhatos.app.aang.Persona
import furhatos.app.aang.gestures.AvatarStateRelease
import furhatos.app.aang.gestures.AvatarStateSurge
import furhatos.app.aang.gestures.PlayfulGrin
import furhatos.app.aang.setting.DISTANCE_TO_ENGAGE
import furhatos.app.aang.setting.MAX_NUMBER_OF_USERS
import furhatos.flow.kotlin.*
import furhatos.flow.kotlin.voice.Voice
import furhatos.gestures.Gestures
import java.awt.Color

private val VOICE_NORMAL = Voice(name = "Justin-Neural")   // young Aang
private val VOICE_AVATAR = Voice(name = "Matthew-Neural")  // deep, booming
private val CALM_BLUE = Color(42, 107, 192)

/** Whether the Avatar State is currently active (drives voice + persona). */
private var avatarActive = false
private var avatarSince = 0L   // System.currentTimeMillis() when the Avatar State ignited
private const val AVATAR_TIMEOUT_MS = 60_000L

val Parent: State = state {
    onUserEnter(instant = true) {
        if (!furhat.isAttendingUser) furhat.attend(it) else furhat.glance(it)
    }
    onUserLeave(instant = true) {
        when {
            !users.hasAny() -> { furhat.attendNobody(); goto(Idle) }
            furhat.isAttending(it) -> furhat.attend(users.other)
        }
    }
}

val Init: State = state {
    init {
        users.setSimpleEngagementPolicy(DISTANCE_TO_ENGAGE, MAX_NUMBER_OF_USERS)
    }
    onEntry {
        furhat.setVoice(VOICE_NORMAL)
        furhat.ledStrip.solid(CALM_BLUE)
        furhat.setCharacter(Persona.FACE)   // wear the custom "Aang" face (official API)
        when {
            furhat.isVirtual() -> goto(Greeting)
            users.hasAny() -> { furhat.attend(users.random); goto(Greeting) }
            else -> goto(Idle)
        }
    }
}

val Idle: State = state {
    onEntry { furhat.attendNobody() }
    onUserEnter {
        furhat.attend(it)
        goto(Greeting)
    }
}

val Greeting: State = state(Parent) {
    onEntry {
        Brain.reset()
        avatarActive = false
        furhat.setVoice(VOICE_NORMAL)
        furhat.gesture(PlayfulGrin)
        furhat.say(Persona.OPENING)
        goto(Conversation)
    }
}

val Conversation: State = state(Parent) {
    onEntry {
        // The Avatar State burns out on its own — it never stays forever.
        if (avatarActive && System.currentTimeMillis() - avatarSince > AVATAR_TIMEOUT_MS) {
            furhat.gesture(AvatarStateRelease)
            furhat.setVoice(VOICE_NORMAL)
            avatarActive = false
        }
        furhat.listen()
    }

    onResponse {
        val text = it.text
        when {
            Persona.matches(text, Persona.QUIT) -> {
                furhat.say("May the spirits watch over you. Goodbye!")
                goto(Idle)
            }
            !avatarActive && Persona.matches(text, Persona.TRIGGERS) -> {
                avatarActive = true
                avatarSince = System.currentTimeMillis()
                furhat.setVoice(VOICE_AVATAR)
                furhat.gesture(AvatarStateSurge)
                furhat.say(Persona.ENTER_LINES.random())
                reentry()
            }
            avatarActive && Persona.matches(text, Persona.DEACTIVATE) -> {
                furhat.gesture(AvatarStateRelease)
                furhat.say(Persona.EXIT_LINES.random())
                furhat.setVoice(VOICE_NORMAL)
                avatarActive = false
                reentry()
            }
            else -> {
                // The LLM is the director: it decides, per turn, whether the moment
                // is dire enough for the Avatar State (or calm enough to leave it).
                val r = Brain.respond(text, avatarActive)
                when {
                    r.wantAvatar && !avatarActive -> {      // stakes turned dire -> surge
                        avatarActive = true
                        avatarSince = System.currentTimeMillis()
                        furhat.setVoice(VOICE_AVATAR)
                        furhat.gesture(AvatarStateSurge)
                        furhat.say(r.text)
                    }
                    !r.wantAvatar && avatarActive -> {       // danger passed -> recede
                        furhat.gesture(AvatarStateRelease)
                        furhat.setVoice(VOICE_NORMAL)
                        avatarActive = false
                        furhat.say(r.text)
                    }
                    else -> {
                        if (!avatarActive) furhat.gesture(Gestures.Thoughtful)
                        furhat.say(r.text)
                    }
                }
                reentry()
            }
        }
    }

    onNoResponse { reentry() }
}
