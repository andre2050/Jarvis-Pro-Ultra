package com.andre.jarvisultra

import org.junit.Assert.*
import org.junit.Test

class LocalCommandParserTest {
    @Test fun nestedArguments() {
        val (name, args) = LocalCommandParser.parseTool("""{"tool":"lanterna","args":{"ligar":true}}""")
        assertEquals("lanterna", name)
        assertTrue(args.getBoolean("ligar"))
    }

    @Test fun nestedObjectsAndArrays() {
        val (_, args) = LocalCommandParser.parseTool("""{"tool":"teste","args":{"config":{"n":2},"items":[{"x":1}]}}""")
        assertEquals(2, args.getJSONObject("config").getInt("n"))
        assertEquals(1, args.getJSONArray("items").getJSONObject(0).getInt("x"))
    }

    @Test fun fencedJson() {
        val (name, _) = LocalCommandParser.parseTool("```json\n{\"tool\":\"hora_data\",\"args\":{}}\n```")
        assertEquals("hora_data", name)
    }

    @Test fun stringsWithBracesEscapesAndQuotes() {
        val (_, args) = LocalCommandParser.parseTool("""{"tool":"teste","args":{"texto":"{ok} \"oi\" C:\\tmp"}}""")
        assertEquals("{ok} \"oi\" C:\\tmp", args.getString("texto"))
    }

    @Test fun acceptsLeadingTextAndSkipsNonCommands() {
        val (name, _) = LocalCommandParser.parseTool("Texto {\"resposta\":\"ok\"} {\"tool\":\"hora_data\"}")
        assertEquals("hora_data", name)
    }

    @Test fun rejectsIncompleteJson() {
        assertNull(LocalCommandParser.parseTool("""{"tool":"lanterna","args":{"ligar":true}""").first)
    }

    @Test fun rejectsInvalidArguments() {
        for (args in listOf("null", "[]", "true", "\"texto\"", "5")) {
            assertNull(LocalCommandParser.parseTool("{\"tool\":\"lanterna\",\"args\":$args}").first)
        }
    }

    @Test fun rejectsInvalidToolNames() {
        for (name in listOf("null", "42", "\"\"", "\"  \"", "{}")) {
            assertNull(LocalCommandParser.parseTool("{\"tool\":$name,\"args\":{}}").first)
        }
    }

    @Test fun plainResponseIsNotCommand() {
        assertNull(LocalCommandParser.parseTool("""{"resposta":"Bom dia, senhor."}""").first)
    }

    @Test fun missingArgsDefaultsToEmptyObject() {
        val (name, args) = LocalCommandParser.parseTool("""{"tool":"hora_data"}""")
        assertEquals("hora_data", name)
        assertEquals(0, args.length())
    }
}
