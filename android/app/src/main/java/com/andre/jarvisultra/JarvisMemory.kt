package com.andre.jarvisultra

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import java.util.Calendar
import java.util.Locale

/**
 * Rede de memória do JARVIS (v2.0): fatos permanentes + histórico de interações,
 * tudo no próprio aparelho (SQLite). Nada sai do celular.
 *
 * - memories: o que o usuário manda guardar ("lembra que...")
 * - interactions: cada mensagem e tool usada, com timestamp — base da previsão de hábitos
 */
object JarvisMemory {
    private const val DB_NAME = "jarvis_memory.db"
    private val STOP = setOf(
        "de", "da", "do", "que", "para", "pra", "pro", "no", "na", "em",
        "me", "meu", "minha", "seu", "sua", "uma", "ums", "com", "sem"
    )

    data class Suggestion(val label: String, val message: String)

    private val targets = mapOf(
        "hora_e_data" to ("que horas são agora?" to "\u26a1 Pelo seu padr\u00e3o, quer que eu d\u00ea as horas?"),
        "piada" to ("me conta uma piada" to "\u26a1 Uma piada agora cairia bem, senhor?"),
        "status_dispositivo" to ("status do dispositivo" to "\u26a1 Verificar o status do dispositivo?")
    )

    private fun db(ctx: Context): SQLiteDatabase =
        ctx.openOrCreateDatabase(DB_NAME, Context.MODE_PRIVATE, null)

    fun ensure(ctx: Context) {
        val d = db(ctx)
        d.execSQL("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, created_at INTEGER NOT NULL)")
        d.execSQL("CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT)")
        d.close()
    }

    /** Guarda um fato permanente (sem duplicar texto igual). */
    fun remember(ctx: Context, fact: String) {
        val t = fact.trim()
        if (t.isEmpty()) return
        ensure(ctx)
        val d = db(ctx)
        val cur = d.rawQuery("SELECT id FROM memories WHERE lower(text)=lower(?) LIMIT 1", arrayOf(t))
        val exists = cur.moveToFirst()
        cur.close()
        if (!exists) {
            d.execSQL("INSERT INTO memories (text, created_at) VALUES (?, ?)", arrayOf(t, System.currentTimeMillis()))
        }
        d.close()
    }

    /**
     * Busca memórias relevantes pra pergunta atual: sobreposição de palavras-chave
     * com um bônus de recência. Sem relação nenhuma, não injeta nada no contexto.
     */
    fun search(ctx: Context, query: String, limit: Int = 5): List<String> {
        ensure(ctx)
        val d = db(ctx)
        val rows = mutableListOf<Pair<String, Long>>()
        val c = d.rawQuery("SELECT text, created_at FROM memories ORDER BY created_at DESC LIMIT 300", null)
        while (c.moveToNext()) rows.add(c.getString(0) to c.getLong(1))
        c.close()
        d.close()
        if (rows.isEmpty()) return emptyList()
        val qTokens = tokens(query)
        if (qTokens.isEmpty()) return emptyList()
        val now = System.currentTimeMillis()
        return rows.mapNotNull { (text, ts) ->
            val overlap = tokens(text).intersect(qTokens).size
            if (overlap == 0) return@mapNotNull null
            val days = ((now - ts) / 86400000.0).coerceAtLeast(0.0)
            val recency = (1.5 - (days / 30.0)).coerceIn(0.0, 1.5)
            Triple(text, overlap * 2.0 + recency, ts)
        }.sortedByDescending { it.second }.take(limit).map { it.first }
    }

    /** Registra toda interação (mensagem ou tool) pra alimentar a previsão de hábitos. */
    /** Painel de transparência: TODAS as memórias com id e data. */
    fun all(ctx: Context): List<Triple<Int, String, Long>> {
        ensure(ctx)
        val d = db(ctx)
        val out = mutableListOf<Triple<Int, String, Long>>()
        val c = d.rawQuery("SELECT id, text, created_at FROM memories ORDER BY created_at DESC", null)
        while (c.moveToNext()) out.add(Triple(c.getInt(0), c.getString(1), c.getLong(2)))
        c.close(); d.close()
        return out
    }

    fun deleteById(ctx: Context, id: Int) {
        ensure(ctx)
        val d = db(ctx)
        d.execSQL("DELETE FROM memories WHERE id=?", arrayOf(id))
        d.close()
    }

    fun deleteAll(ctx: Context) {
        ensure(ctx)
        val d = db(ctx)
        d.execSQL("DELETE FROM memories")
        d.close()
    }

    /** Últimos fatos guardados (pra "o que você sabe de mim"). */
    fun recent(ctx: Context, limit: Int = 10): List<String> {
        ensure(ctx)
        val d = db(ctx)
        val out = mutableListOf<String>()
        val c = d.rawQuery("SELECT text FROM memories ORDER BY created_at DESC LIMIT ?", arrayOf(limit.toString()))
        while (c.moveToNext()) out.add(c.getString(0))
        c.close()
        d.close()
        return out
    }

    fun logInteraction(ctx: Context, kind: String, detail: String) {
        ensure(ctx)
        val d = db(ctx)
        d.execSQL(
            "INSERT INTO interactions (ts, kind, detail) VALUES (?, ?, ?)",
            arrayOf(System.currentTimeMillis().toString(), kind, detail)
        )
        d.close()
    }

    /**
     * Previsão de hábito: olha as tools usadas nas \u00faltimas 500 intera\u00e7\u00f5es,
     * prioriza o que costuma ser usado nesta faixa de hor\u00e1rio, e sugere antes de o
     * usu\u00e1rio pedir. Retorna null enquanto n\u00e3o tem padr\u00e3o suficiente.
     */
    fun suggest(ctx: Context): Suggestion? {
        ensure(ctx)
        val d = db(ctx)
        val rows = mutableListOf<Pair<Long, String>>()
        val c = d.rawQuery("SELECT ts, kind FROM interactions ORDER BY ts DESC LIMIT 500", null)
        while (c.moveToNext()) rows.add(c.getLong(0) to c.getString(1))
        c.close()
        d.close()
        val toolRows = rows.filter { it.second in targets }
        if (toolRows.size < 2) return null

        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        val window = toolRows.filter { (ts, _) ->
            val c2 = Calendar.getInstance().apply { timeInMillis = ts }
            val h = c2.get(Calendar.HOUR_OF_DAY)
            ((h - hour + 24) % 24) <= 2
        }
        val pool = if (window.size >= 2) window else toolRows
        val top = pool.groupingBy { it.second }.eachCount().maxByOrNull { it.value } ?: return null
        val (message, label) = targets[top.key] ?: return null
        return Suggestion(label, message)
    }

    private fun tokens(s: String): Set<String> =
        s.lowercase(Locale("pt", "BR"))
            .split(Regex("[^a-z\u00e0-\u00ff0-9]+"))
            .filter { it.length > 2 && it !in STOP }
            .toSet()
}
