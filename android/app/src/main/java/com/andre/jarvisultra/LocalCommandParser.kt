package com.andre.jarvisultra

import org.json.JSONObject

/** Reads complete JSON objects, including nested arguments and escaped strings. */
internal object LocalCommandParser {
    fun parseTool(output: String): Pair<String?, JSONObject> {
        for (text in objects(output)) {
            val json = try { JSONObject(text) } catch (_: Exception) { continue }
            if (!json.has("tool")) continue
            val name = (json.opt("tool") as? String)?.trim()
            if (name.isNullOrEmpty()) return Pair(null, JSONObject())
            // Never execute a malformed argument value with silently empty arguments.
            val args = if (!json.has("args")) JSONObject()
                else json.opt("args") as? JSONObject ?: return Pair(null, JSONObject())
            return Pair(name, args)
        }
        return Pair(null, JSONObject())
    }

    private fun objects(output: String): Sequence<String> = sequence {
        var start = -1
        var depth = 0
        var quoted = false
        var escaped = false
        for (index in output.indices) {
            val char = output[index]
            if (depth == 0) {
                if (char == '{') {
                    start = index
                    depth = 1
                    quoted = false
                    escaped = false
                }
                continue
            }
            if (quoted) {
                when {
                    escaped -> escaped = false
                    char == '\\' -> escaped = true
                    char == '"' -> quoted = false
                }
                continue
            }
            when (char) {
                '"' -> quoted = true
                '{' -> depth++
                '}' -> {
                    depth--
                    if (depth == 0) yield(output.substring(start, index + 1))
                }
            }
        }
    }
}
