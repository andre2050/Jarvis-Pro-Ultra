package com.andre.jarvisultra

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.media.AudioManager
import android.net.Uri
import android.os.BatteryManager
import androidx.core.content.ContextCompat
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * Percepção Total (v4.0.0): o JARVIS passa a SENTIR o mundo e o aparelho.
 * - Clima real via GPS (Open-Meteo, sem chave de API)
 * - Onde o senhor está (GPS + endereço via OpenStreetMap)
 * - Navegação (abre o mapa com direções)
 * - Música por voz (YouTube/Spotify)
 * - Controle de volume
 * - Contexto vivo do aparelho (bateria/hora/volume) injetado no prompt do cérebro
 */
object JarvisPercepcao {

    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .dns(FallbackDns)
        .build()

    fun declarations(): JSONArray {
        val clima = JSONObject()
            .put("name", "clima")
            .put("description", "Previsão do tempo AGORA na localização do senhor (via GPS). Use quando ele perguntar sobre clima, tempo, chuva, calor ou o que vestir.")
            .put("parameters", JSONObject().put("type", "object").put("properties", JSONObject()))

        val onde = JSONObject()
            .put("name", "onde_estou")
            .put("description", "Diz onde o senhor está agora: bairro, cidade e estado, via GPS + OpenStreetMap.")
            .put("parameters", JSONObject().put("type", "object").put("properties", JSONObject()))

        val navegar = JSONObject()
            .put("name", "navegar_para")
            .put("description", "Abre o mapa com a rota até um destino. Use quando o senhor pedir pra ir/levar até um lugar.")
            .put(
                "parameters",
                JSONObject()
                    .put("type", "object")
                    .put(
                        "properties",
                        JSONObject().put(
                            "destino",
                            JSONObject().put("type", "string").put("description", "Endereço ou ponto de destino, ex: 'shopping recife' ou 'rua xv de novembro, 100'")
                        )
                    )
                    .put("required", JSONArray().put("destino"))
            )

        val musica = JSONObject()
            .put("name", "tocar_musica")
            .put("description", "Abre o YouTube (ou Spotify) buscando pela música/artista. Use quando o senhor pedir pra tocar música.")
            .put(
                "parameters",
                JSONObject()
                    .put("type", "object")
                    .put(
                        "properties",
                        JSONObject().put(
                            "busca",
                            JSONObject().put("type", "string").put("description", "Nome da música e/ou artista, ex: 'iron maiden fear of the dark'")
                        )
                    )
                    .put("required", JSONArray().put("busca"))
            )

        val volume = JSONObject()
            .put("name", "controlar_volume")
            .put("description", "Controla o volume multimídia do celular: aumentar, diminuir, silenciar ou máximo. Sem argumentos, informa o volume atual.")
            .put(
                "parameters",
                JSONObject()
                    .put("type", "object")
                    .put(
                        "properties",
                        JSONObject().put(
                            "acao",
                            JSONObject()
                                .put("type", "string")
                                .put("enum", JSONArray().put("aumentar").put("diminuir").put("silenciar").put("maximo"))
                                .put("description", "Ação de volume desejada")
                        )
                    )
            )

        return JSONArray().put(clima).put(onde).put(navegar).put(musica).put(volume)
    }

    /** Executa uma tool deste módulo; retorna null se não for daqui. */
    fun execute(ctx: Context, name: String, args: JSONObject): String? = try {
        when (name) {
            "clima" -> clima(ctx)
            "onde_estou" -> ondeEstou(ctx)
            "navegar_para" -> navegarPara(ctx, args.getString("destino"))
            "tocar_musica" -> tocarMusica(ctx, args.getString("busca"))
            "controlar_volume" -> controlarVolume(ctx, args)
            else -> null
        }
    } catch (e: Exception) {
        "erro ao executar '$name': ${e.message}"
    }

    /** Contexto vivo injetado no prompt do cérebro a cada turno — o JARVIS SABE sem tools. */
    fun contextoDoAparelho(ctx: Context): String {
        return try {
            val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
            val pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY).coerceIn(0, 100)
            val charging = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_STATUS) == BatteryManager.BATTERY_STATUS_CHARGING
            val hora = SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(Date())
            val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val vol = am.getStreamVolume(AudioManager.STREAM_MUSIC)
            val maxVol = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            val energia = if (charging) "carregando" else "na bateria"
            "Contexto do aparelho AGORA: são $hora, bateria em $pct% ($energia), volume multimídia $vol de $maxVol."
        } catch (e: Exception) { "" }
    }

    // ---------- GPS ----------

    private fun temLocalizacao(ctx: Context): Boolean =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun ultimaLocalizacao(ctx: Context): Pair<Double, Double>? {
        if (!temLocalizacao(ctx)) return null
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        for (p in listOf(LocationManager.NETWORK_PROVIDER, LocationManager.PASSIVE_PROVIDER, LocationManager.GPS_PROVIDER)) {
            try {
                val l = lm.getLastKnownLocation(p) ?: continue
                return Pair(l.latitude, l.longitude)
            } catch (_: SecurityException) { } catch (_: Exception) { }
        }
        return null
    }

    private fun ondeEstou(ctx: Context): String {
        val loc = ultimaLocalizacao(ctx)
            ?: return "sem permissão de localização, senhor — autorize nas permissões do app que eu passo a saber onde estamos."
        val (lat, lon) = loc
        val endereco = try {
            val req = Request.Builder()
                .url("https://nominatim.openstreetmap.org/reverse?lat=$lat&lon=$lon&format=json&accept-language=pt-BR")
                .header("User-Agent", "JarvisUltra/4.0 (Android; assistente pessoal)")
                .build()
            http.newCall(req).execute().use { r ->
                if (r.isSuccessful) {
                    val j = JSONObject(r.body!!.string())
                    val addr = j.optJSONObject("address")
                    if (addr != null) {
                        val bairro = addr.optString("suburb", addr.optString("neighbourhood", ""))
                        val cidade = addr.optString("city", addr.optString("town", addr.optString("village", "")))
                        val estado = addr.optString("state", "")
                        listOf(bairro, cidade, estado).filter { it.isNotBlank() }.joinToString(", ")
                    } else j.optString("display_name", "")
                } else ""
            }
        } catch (_: Exception) { "" }
        return if (endereco.isBlank()) "coordenadas atuais: $lat, $lon — não consegui o endereço agora, senhor"
        else "o senhor está em $endereco (coordenadas $lat, $lon)"
    }

    // ---------- clima ----------

    private fun clima(ctx: Context): String {
        val loc = ultimaLocalizacao(ctx)
            ?: return "sem permissão de localização, senhor — autorize nas permissões do app que eu vejo o clima da sua região."
        val (lat, lon) = loc
        return try {
            val url = "https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon" +
                "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m" +
                "&daily=temperature_2m_max,temperature_2m_min,weather_code&forecast_days=1&timezone=auto"
            http.newCall(Request.Builder().url(url).build()).execute().use { r ->
                if (!r.isSuccessful) return "o serviço de clima respondeu ${r.code}, senhor"
                val j = JSONObject(r.body!!.string())
                val cur = j.getJSONObject("current")
                val dia = j.getJSONObject("daily")
                val t = cur.getDouble("temperature_2m")
                val sens = cur.getDouble("apparent_temperature")
                val umi = cur.getInt("relative_humidity_2m")
                val vento = cur.getDouble("wind_speed_10m")
                val cond = descrever(cur.optInt("weather_code", 0))
                val max = dia.getJSONArray("temperature_2m_max").getDouble(0)
                val min = dia.getJSONArray("temperature_2m_min").getDouble(0)
                val condDia = descrever(dia.getJSONArray("weather_code").optInt(0, 0))
                "clima AGORA na sua posição: $t°C (sensação de $sens°C), $cond, umidade $umi%, vento a ${vento}km/h. Hoje: mínima de $min°C, máxima de $max°C, $condDia."
            }
        } catch (e: Exception) { "não consegui buscar o clima, senhor: ${e.message}" }
    }

    private fun descrever(code: Int): String = when (code) {
        0 -> "céu limpo"
        1, 2 -> "parcialmente nublado"
        3 -> "nublado"
        45, 48 -> "com neblina"
        in 51..57 -> "com garoa"
        in 61..67 -> "com chuva"
        in 71..77 -> "com neve"
        in 80..82 -> "com pancadas de chuva"
        in 85..86 -> "com pancadas de neve"
        in 95..99 -> "com tempestade"
        else -> "condição climática código $code"
    }

    // ---------- ações ----------

    private fun navegarPara(ctx: Context, destino: String): String {
        return try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/maps/dir/?api=1&destination=" + Uri.encode(destino)))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(intent)
            "abrindo a navegação até $destino, senhor — boa viagem"
        } catch (e: Exception) { "não achei app de mapa no aparelho: ${e.message}" }
    }

    private fun tocarMusica(ctx: Context, busca: String): String {
        val tentativas = listOf(
            "https://www.youtube.com/results?search_query=" + Uri.encode(busca),
            "https://music.youtube.com/search?q=" + Uri.encode(busca),
            "https://open.spotify.com/search/" + Uri.encode(busca)
        )
        for (u in tentativas) {
            try {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(u))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                ctx.startActivity(intent)
                return "abri a busca por '$busca', senhor — é só dar o play"
            } catch (_: Exception) { }
        }
        return "nenhum app de música atendeu ao chamado, senhor"
    }

    private fun controlarVolume(ctx: Context, args: JSONObject): String {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        val acao = args.optString("acao", "")
        return when (acao) {
            "aumentar" -> {
                am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, 0)
                "volume aumentado para ${am.getStreamVolume(AudioManager.STREAM_MUSIC)} de $max"
            }
            "diminuir" -> {
                am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER, 0)
                "volume diminuído para ${am.getStreamVolume(AudioManager.STREAM_MUSIC)} de $max"
            }
            "silenciar" -> {
                am.setStreamVolume(AudioManager.STREAM_MUSIC, 0, 0)
                "volume silenciado, senhor"
            }
            "maximo" -> {
                am.setStreamVolume(AudioManager.STREAM_MUSIC, max, 0)
                "volume no máximo ($max), senhor"
            }
            else -> "volume multimídia atual: ${am.getStreamVolume(AudioManager.STREAM_MUSIC)} de $max (posso: aumentar, diminuir, silenciar ou maximo)"
        }
    }
}
