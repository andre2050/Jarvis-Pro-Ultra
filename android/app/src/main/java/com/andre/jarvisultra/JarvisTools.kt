package com.andre.jarvisultra

import android.content.Context
import android.os.BatteryManager
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.random.Random

/**
 * Registry de tools do JARVIS Android (equivalente ao tools_manifest.py do desktop).
 * Cada tool declara seu schema pro Gemini e tem um executor local.
 */
object JarvisTools {

    fun declarations(): JSONArray {
        val calc = JSONObject()
            .put("name", "calcular")
            .put(
                "description",
                "Calcula uma expressão matemática com + - * / % e parênteses. Ex: 'calcular 15% de 230' vira '230*15/100'."
            )
            .put(
                "parameters",
                JSONObject()
                    .put("type", "object")
                    .put(
                        "properties",
                        JSONObject().put(
                            "expressao",
                            JSONObject()
                                .put("type", "string")
                                .put("description", "Expressão matemática, ex: (12+8)*3")
                        )
                    )
                    .put("required", JSONArray().put("expressao"))
            )

        val hora = JSONObject()
            .put("name", "hora_e_data")
            .put("description", "Informa a hora e a data atuais no fuso do dispositivo.")
            .put("parameters", JSONObject().put("type", "object").put("properties", JSONObject()))

        val dev = JSONObject()
            .put("name", "status_dispositivo")
            .put("description", "Mostra modelo, versão do Android, bateria e memória disponível do dispositivo.")
            .put("parameters", JSONObject().put("type", "object").put("properties", JSONObject()))

        val lembrar = JSONObject()
            .put("name", "lembrar_fato")
            .put(
                "description",
                "Guarda um fato permanente sobre o usu\u00e1rio na mem\u00f3ria de longo prazo do JARVIS. Use quando ele pedir para lembrar/guardar informa\u00e7\u00e3o (prefer\u00eancias, nomes, compromissos, rotinas)."
            )
            .put(
                "parameters",
                JSONObject()
                    .put("type", "object")
                    .put(
                        "properties",
                        JSONObject().put(
                            "fato",
                            JSONObject()
                                .put("type", "string")
                                .put("description", "O fato em uma frase curta, ex: 'a reuniao do Andre e sexta as 15h'")
                        )
                    )
                    .put("required", JSONArray().put("fato"))
            )

        val piada = JSONObject()
            .put("name", "piada")
            .put("description", "Conta uma piada curta em português para levantar o humor do usuário.")
            .put("parameters", JSONObject().put("type", "object").put("properties", JSONObject()))

        val r = JSONArray().put(calc).put(hora).put(dev).put(piada).put(lembrar)
        val phone = JarvisPhoneTools.declarations()
        for (i in 0 until phone.length()) r.put(phone.get(i))
        val percepcao = JarvisPercepcao.declarations()
        for (i in 0 until percepcao.length()) r.put(percepcao.get(i))
        val visao = JarvisVisao.declarations()
        for (i in 0 until visao.length()) r.put(visao.get(i))
        return r
    }

    /** Executa uma tool chamada pelo Gemini. Retorna o resultado como string. */
    fun execute(ctx: Context, name: String, args: JSONObject): String = try {
        when (name) {
            "calcular" -> calcular(args.getString("expressao"))
            "hora_e_data" -> horaEData()
            "status_dispositivo" -> statusDispositivo(ctx)
            "piada" -> piadaAleatoria()
            "lembrar_fato" -> lembrarFato(ctx, args.getString("fato"))
            else -> JarvisVisao.execute(ctx, name, args)
                ?: JarvisPercepcao.execute(ctx, name, args)
                ?: JarvisPhoneTools.execute(ctx, name, args)
                ?: "tool desconhecida: $name"
        }
    } catch (e: Exception) {
        "erro ao executar '$name': ${e.message}"
    }

    // ---------- executores ----------

    private fun calcular(expr: String): String {
        val v = evalExpr(expr)
        return if (v == v.toLong().toDouble()) "resultado: ${v.toLong()}" else "resultado: $v"
    }

    private fun horaEData(): String {
        val h = SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(Date())
        val d = SimpleDateFormat("EEEE, d 'de' MMMM 'de' yyyy", Locale("pt", "BR")).format(Date())
        return "agora são $h de hoje, $d"
    }

    private fun statusDispositivo(ctx: Context): String {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val rt = Runtime.getRuntime()
        val memMb = (rt.maxMemory() - rt.totalMemory() + rt.freeMemory()) / (1024 * 1024)
        return "dispositivo: ${Build.MODEL}, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}), " +
            "bateria em ${pct.coerceIn(0, 100)}%, ~${memMb}MB de heap livre"
    }

    private val piadas = listOf(
        "Por que o livro de matemática se suicidou? Porque tinha muitos problemas.",
        "O que o zero disse pro oito? Belo cinto, amigo.",
        "Por que o computador foi preso? Por excesso de byte.",
        "Qual é o contrário de volátil? Vem cá, sobrinho.",
        "Meu PC tem 8 GB de RAM e ainda pergunta se quero continuar assim. Sim, PC. Todos queremos."
    )

    private fun piadaAleatoria(): String = piadas[Random.nextInt(piadas.size)]

    private fun lembrarFato(ctx: Context, fato: String): String {
        JarvisMemory.remember(ctx, fato)
        return "fato guardado na memoria permanente do JARVIS: '$fato'"
    }

    // ---------- parser matemático seguro (sem eval) ----------

    /** Parser recursivo: expr -> term (+|- term)* ; term -> factor (*|/|% factor)* */
    private class MathParser(private val s: String) {
        private var i = 0

        fun parse(): Double {
            val v = expr()
            skip()
            if (i < s.length) throw IllegalArgumentException("símbolo inesperado")
            return v
        }

        private fun expr(): Double {
            var v = term()
            while (true) {
                skip()
                if (i < s.length && s[i] == '+') { i++; v += term() }
                else if (i < s.length && s[i] == '-') { i++; v -= term() }
                else return v
            }
        }

        private fun term(): Double {
            var v = factor()
            while (true) {
                skip()
                if (i < s.length && s[i] == '*') { i++; v *= factor() }
                else if (i < s.length && s[i] == '/') {
                    i++
                    val d = factor()
                    v = if (d == 0.0) throw ArithmeticException("divisão por zero") else v / d
                } else if (i < s.length && s[i] == '%') { i++; v = v % factor() }
                else return v
            }
        }

        private fun factor(): Double {
            skip()
            if (i < s.length && s[i] == '+') { i++; return factor() }
            if (i < s.length && s[i] == '-') { i++; return -factor() }
            if (i < s.length && s[i] == '(') {
                i++
                val v = expr()
                skip()
                if (i >= s.length || s[i] != ')') throw IllegalArgumentException("parêntese não fechado")
                i++
                return v
            }
            return number()
        }

        private fun number(): Double {
            skip()
            val st = i
            while (i < s.length && (s[i].isDigit() || s[i] == '.')) i++
            if (st == i) throw IllegalArgumentException("número esperado")
            return s.substring(st, i).toDouble()
        }

        private fun skip() {
            while (i < s.length && s[i].isWhitespace()) i++
        }
    }

    fun evalExpr(expr: String): Double =
        MathParser(expr.replace(",", ".").replace("x", "*", ignoreCase = true)).parse()
}
