package furhatos.app.aang

import furhatos.app.aang.flow.Init
import furhatos.flow.kotlin.Flow
import furhatos.skills.Skill

class AangSkill : Skill() {
    override fun start() {
        Flow().run(Init)
    }
}

fun main(args: Array<String>) {
    Skill.main(args)
}
