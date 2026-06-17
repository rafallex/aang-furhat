package furhatos.app.aang

import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * LLM conversational brain (Groq, OpenAI-compatible). Reads GROQ_API_KEY from the
 * environment. If no key is set or a call fails, falls back to in-character lines
 * so the skill never hard-stops.
 */
/** A reply plus the Avatar-State decision the LLM made this turn. */
data class BrainReply(val wantAvatar: Boolean, val text: String)

object Brain {
    private val apiKey: String? = System.getenv("GROQ_API_KEY")
    private val model: String = System.getenv("AANG_MODEL") ?: "llama-3.3-70b-versatile"
    private val gson = Gson()
    private val history = mutableListOf<Pair<String, String>>()  // (role, content)

    fun reset() = history.clear()

    fun respond(userText: String, avatar: Boolean): BrainReply {
        history.add("user" to userText)
        while (history.size > 24) history.removeAt(0)
        val key = apiKey ?: return BrainReply(avatar, Persona.FALLBACKS.random())
        return try {
            val raw = callGroq(key, if (avatar) Persona.SYSTEM_AVATAR else Persona.SYSTEM_NORMAL)
            val reply = parse(raw, avatar)
            history.add("assistant" to reply.text)
            reply
        } catch (e: Exception) {
            println("[brain] groq call failed: ${e.message}")
            BrainReply(avatar, Persona.FALLBACKS.random())
        }
    }

    /** Read the [CALM]/[AVATAR] control tag, then strip it from the spoken text.
     *  No tag -> keep the current state. */
    private fun parse(raw: String, current: Boolean): BrainReply {
        val upper = raw.uppercase()
        val wantAvatar = when {
            upper.contains("[AVATAR]") -> true
            upper.contains("[CALM]") -> false
            else -> current
        }
        val text = raw.replace(Regex("(?i)\\[\\s*(avatar|calm)\\s*]"), "").trim()
        return BrainReply(wantAvatar, if (text.isNotEmpty()) text else Persona.FALLBACKS.random())
    }

    private fun callGroq(key: String, system: String): String {
        val messages = JsonArray()
        messages.add(message("system", system))
        history.forEach { messages.add(message(it.first, it.second)) }

        val body = JsonObject().apply {
            addProperty("model", model)
            add("messages", messages)
            addProperty("temperature", 0.85)
            addProperty("max_tokens", 160)
        }

        val conn = (URL("https://api.groq.com/openai/v1/chat/completions").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = 20000
            readTimeout = 20000
            setRequestProperty("Authorization", "Bearer $key")
            setRequestProperty("Content-Type", "application/json")
        }
        OutputStreamWriter(conn.outputStream, Charsets.UTF_8).use { it.write(gson.toJson(body)) }
        val text = conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        return JsonParser.parseString(text).asJsonObject
            .getAsJsonArray("choices").get(0).asJsonObject
            .getAsJsonObject("message").get("content").asString.trim()
    }

    private fun message(role: String, content: String) = JsonObject().apply {
        addProperty("role", role)
        addProperty("content", content)
    }
}
