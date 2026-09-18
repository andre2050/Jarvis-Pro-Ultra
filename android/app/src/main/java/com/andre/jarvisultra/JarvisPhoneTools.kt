package com.andre.jarvisultra

import android.provider.AlarmClock
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.net.Uri
import android.provider.CalendarContract
import android.provider.ContactsContract
import android.provider.Settings
import android.telephony.SmsManager
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder

/**
 * Pacote "Controle Total" (v2.1.0): tools que operam o telefone do senhor.
 * Sem root — tudo por permissões oficiais do Android.
 */
object JarvisPhoneTools {

    fun declarations(): JSONArray {
        fun obj(name: String, desc: String, props: JSONObject? = null, required: JSONArray? = null): JSONObject {
            val d = JSONObject().put("name", name).put("description", desc)
                .put("parameters", JSONObject().put("type", "object")
                    .put("properties", props ?: JSONObject()))
            if (required != null) d.getJSONObject("parameters").put("required", required)
            return d
        }
        val r = JSONArray()

        r.put(obj("ligar_para",
            "Liga para um contato pelo nome (ex: 'ligar pra Edna') ou número direto. O discador disca na hora.",
            JSONObject()
                .put("quem", JSONObject().put("type", "string").put("description", "nome do contato, ex: 'Edna'"))
                .put("numero", JSONObject().put("type", "string").put("description", "número com DDD se já souber, ex: '11999998888'")),
            JSONArray().put("quem")))

        r.put(obj("whatsapp",
            "Abre o chat do WhatsApp do contato com a mensagem já escrita — o usuário só toca em enviar. Use SEMPRE que ele pedir para mandar mensagem no WhatsApp.",
            JSONObject()
                .put("quem", JSONObject().put("type", "string").put("description", "nome do contato"))
                .put("numero", JSONObject().put("type", "string").put("description", "número com DDD, opcional se souber"))
                .put("mensagem", JSONObject().put("type", "string").put("description", "o texto da mensagem")),
            JSONArray().put("quem").put("mensagem")))

        r.put(obj("enviar_sms",
            "Envia um SMS direto, sem sair do app.",
            JSONObject()
                .put("quem", JSONObject().put("type", "string").put("description", "nome do contato ou número"))
                .put("numero", JSONObject().put("type", "string").put("description", "número, opcional"))
                .put("mensagem", JSONObject().put("type", "string").put("description", "texto do SMS")),
            JSONArray().put("quem").put("mensagem")))

        r.put(obj("ler_sms",
            "Lê os últimos SMS recebidos na caixa de entrada.",
            JSONObject().put("quantidade", JSONObject().put("type", "integer").put("description", "quantos, padrão 5"))))

        r.put(obj("ler_notificacoes",
            "Lê as últimas mensagens capturadas do WhatsApp e SMS via notificações (precisa do leitor ativado uma vez).",
            JSONObject().put("quantidade", JSONObject().put("type", "integer").put("description", "quantas, padrão 5"))))

        r.put(obj("ativar_notificacoes",
            "Abre a tela do Android para o usuário autorizar o JARVIS a ler notificações. Chame quando o leitor ainda não estiver ativado."))

        r.put(obj("definir_alarme",
            "Define um alarme no relógio do celular.",
            JSONObject()
                .put("hora", JSONObject().put("type", "integer").put("description", "hora 0-23"))
                .put("minuto", JSONObject().put("type", "integer").put("description", "minuto 0-59, padrão 0"))
                .put("rotulo", JSONObject().put("type", "string").put("description", "nome do alarme, opcional")),
            JSONArray().put("hora")))

        r.put(obj("lanterna",
            "Liga ou desliga a lanterna (flash) do celular.",
            JSONObject().put("acao", JSONObject().put("type", "string").put("enum", JSONArray().put("ligar").put("desligar"))),
            JSONArray().put("acao")))

        r.put(obj("definir_timer",
            "Define um timer/cronômetro, ex: 'timer de 10 minutos'.",
            JSONObject()
                .put("minutos", JSONObject().put("type", "integer").put("description", "duração em minutos"))
                .put("rotulo", JSONObject().put("type", "string").put("description", "nome, opcional")),
            JSONArray().put("minutos")))

        r.put(obj("pesquisar_web",
            "Abre o navegador pesquisando algo no Google, ex: 'pesquisa previsão do tempo em São Paulo'.",
            JSONObject().put("consulta", JSONObject().put("type", "string").put("description", "o que pesquisar")),
            JSONArray().put("consulta")))

        r.put(obj("listar_memorias",
            "Conta o que o JARVIS lembra do usuário — fatos guardados na memória de longo prazo.",
            JSONObject().put("quantidade", JSONObject().put("type", "integer").put("description", "quantos, padrão 10"))))

        r.put(obj("abrir_app",
            "Abre um app instalado pelo nome COMUM, sem mistério: 'abrir email' abre o Gmail, 'abrir zap' o WhatsApp, 'abrir navegador', 'abrir mapa', 'abrir agenda', 'abrir play store', 'abrir instagram' e qualquer outro app pelo nome.",
            JSONObject().put("nome", JSONObject().put("type", "string").put("description", "nome do app")),
            JSONArray().put("nome")))

        r.put(obj("abrir_modo_mesa",
            "Abre o Modo Mesa/Carro: painel holográfico em tela cheia sempre ligado, com relógio, clima ao vivo e bateria. Use quando o senhor pedir 'modo mesa', 'modo carro' ou 'painel'."))

        r.put(obj("criar_lembrete",
            "Cria um evento na agenda do celular. VOCÊ calcula a data e hora do pedido e passa em milissegundos Unix. Ex: 'lembrete do dentista amanhã às 15h'.",
            JSONObject()
                .put("titulo", JSONObject().put("type", "string").put("description", "título do evento"))
                .put("inicio_ms", JSONObject().put("type", "integer").put("description", "início em milissegundos Unix (epoch) — calcule a partir do pedido do senhor"))
                .put("minutos", JSONObject().put("type", "integer").put("description", "duração em minutos, padrão 60")),
            JSONArray().put("titulo").put("inicio_ms")))

        r.put(obj("enviar_email",
            "Abre o app de email com a mensagem pronta — o senhor só confere e toca em enviar.",
            JSONObject()
                .put("para", JSONObject().put("type", "string").put("description", "email do destinatário"))
                .put("assunto", JSONObject().put("type", "string").put("description", "assunto, opcional"))
                .put("corpo", JSONObject().put("type", "string").put("description", "texto da mensagem, opcional")),
            JSONArray().put("para")))

        return r
    }

    /** Executa uma tool de telefone; null se não for conhecida aqui. */
    fun execute(ctx: Context, name: String, args: JSONObject): String? = try {
        when (name) {
            "ligar_para" -> ligarPara(ctx, args)
            "whatsapp" -> whatsapp(ctx, args)
            "enviar_sms" -> enviarSms(ctx, args)
            "ler_sms" -> lerSms(ctx, args)
            "ler_notificacoes" -> lerNotificacoes(args)
            "ativar_notificacoes" -> ativarNotificacoes(ctx)
            "definir_alarme" -> definirAlarme(ctx, args)
            "lanterna" -> lanterna(ctx, args)
            "abrir_app" -> abrirApp(ctx, args)
            "definir_timer" -> definirTimer(ctx, args)
            "pesquisar_web" -> pesquisarWeb(ctx, args)
            "listar_memorias" -> listarMemorias(ctx, args)
            "abrir_modo_mesa" -> abrirModoMesa(ctx)
            "criar_lembrete" -> criarLembrete(ctx, args)
            "enviar_email" -> enviarEmail(ctx, args)
            else -> null
        }
    } catch (e: Exception) {
        "erro em '" + name + "': " + (e.message ?: "falha desconhecida")
    }

    // ---------- infra ----------

    private fun temPermissao(ctx: Context, p: String): Boolean =
        ctx.checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED

    private fun limparNumero(n: String): String = n.filter { it.isDigit() || it == '+' }

    private fun acharContato(ctx: Context, nome: String): Pair<String, String>? {
        if (!temPermissao(ctx, android.Manifest.permission.READ_CONTACTS)) return null
        val cur = ctx.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            arrayOf(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER,
                ContactsContract.CommonDataKinds.Phone.NORMALIZED_NUMBER
            ), null, null, null
        ) ?: return null
        val q = nome.trim().lowercase()
        var achado: Pair<String, String>? = null
        while (cur.moveToNext()) {
            val dn = cur.getString(0) ?: continue
            val num = cur.getString(2) ?: cur.getString(1) ?: continue
            if (dn.lowercase().contains(q)) { achado = dn to num; break }
        }
        cur.close()
        return achado
    }

    private fun resolverNumero(ctx: Context, quem: String, numero: String?): String? {
        if (numero != null && numero.isNotBlank()) return limparNumero(numero)
        return acharContato(ctx, quem)?.second?.let { limparNumero(it) }
    }

    // ---------- executores ----------

    private fun ligarPara(ctx: Context, args: JSONObject): String {
        val quem = args.optString("quem")
        val numero = resolverNumero(ctx, quem, args.optString("numero").ifBlank { null })
            ?: return "não encontrei '" + quem + "' nos contatos, senhor. Confirme o nome ou use o número direto."
        val acao = if (temPermissao(ctx, android.Manifest.permission.CALL_PHONE)) Intent.ACTION_CALL else Intent.ACTION_DIAL
        ctx.startActivity(Intent(acao, Uri.parse("tel:" + numero)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        return "ligando para " + quem + " (" + numero + "), senhor."
    }

    private fun whatsapp(ctx: Context, args: JSONObject): String {
        val quem = args.optString("quem")
        val msg = args.optString("mensagem")
        val digitos = resolverNumero(ctx, quem, args.optString("numero").ifBlank { null })?.filter { it.isDigit() }
        if (digitos.isNullOrEmpty() || digitos.length < 10) return "não achei número de WhatsApp para '" + quem + "', senhor."
        val uri = Uri.parse("https://wa.me/" + digitos + "?text=" + URLEncoder.encode(msg, "UTF-8"))
        val i = Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val wa = try { ctx.packageManager.getPackageInfo("com.whatsapp", 0); "com.whatsapp" } catch (e: Exception) {
            try { ctx.packageManager.getPackageInfo("com.whatsapp.w4b", 0); "com.whatsapp.w4b" } catch (e2: Exception) { null }
        }
        if (wa != null) i.setPackage(wa)
        ctx.startActivity(i)
        return "abri o chat do WhatsApp de " + quem + " com a mensagem pronta, senhor — só tocar no envio pra confirmar."
    }

    private fun enviarSms(ctx: Context, args: JSONObject): String {
        if (!temPermissao(ctx, android.Manifest.permission.SEND_SMS))
            return "sem permissão de SMS, senhor — autorize o JARVIS nas permissões do Android."
        val quem = args.optString("quem")
        val numero = resolverNumero(ctx, quem, args.optString("numero").ifBlank { null })
            ?: return "não encontrei o número de '" + quem + "', senhor."
        SmsManager.getDefault().sendTextMessage(numero, null, args.optString("mensagem"), null, null)
        return "SMS enviado para " + quem + " (" + numero + "), senhor."
    }

    private fun lerSms(ctx: Context, args: JSONObject): String {
        if (!temPermissao(ctx, android.Manifest.permission.READ_SMS))
            return "sem permissão para ler SMS, senhor."
        val n = args.optInt("quantidade", 5).coerceIn(1, 10)
        val cur = ctx.contentResolver.query(
            Uri.parse("content://sms/inbox"), arrayOf("address", "body"), null, null, "date DESC"
        ) ?: return "caixa de entrada vazia, senhor."
        val sb = StringBuilder()
        var i = 0
        while (cur.moveToNext() && i < n) {
            sb.append(cur.getString(0)).append(": ").append(cur.getString(1)).append("\n")
            i++
        }
        cur.close()
        return if (sb.isEmpty()) "nenhum SMS na caixa de entrada, senhor."
        else "últimos SMS:\n" + sb.toString().trim()
    }

    private fun lerNotificacoes(args: JSONObject): String {
        val n = args.optInt("quantidade", 5).coerceIn(1, 10)
        val lista = JarvisNotificationStore.recent(n)
        return if (lista.isEmpty())
            "nenhuma notificação capturada ainda, senhor. Se o leitor ainda não foi ativado, me peça 'ativar notificações'."
        else "últimas mensagens capturadas:\n" + lista.joinToString("\n")
    }

    private fun ativarNotificacoes(ctx: Context): String {
        ctx.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        return "abri a tela de acesso a notificações do Android, senhor — toque em 'JARVIS PRO ULTRA' e autorize. É só uma vez."
    }

    private fun definirAlarme(ctx: Context, args: JSONObject): String {
        val h = args.optInt("hora", -1)
        val m = args.optInt("minuto", 0)
        if (h < 0 || h > 23 || m < 0 || m > 59) return "me diga a hora, senhor, ex: 'alarme às 7h30'."
        val i = Intent(AlarmClock.ACTION_SET_ALARM).apply {
            putExtra(AlarmClock.EXTRA_HOUR, h)
            putExtra(AlarmClock.EXTRA_MINUTES, m)
            putExtra(AlarmClock.EXTRA_MESSAGE, args.optString("rotulo").ifBlank { "JARVIS" })
            putExtra(AlarmClock.EXTRA_SKIP_UI, true)
        }.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (i.resolveActivity(ctx.packageManager) == null) return "não achei o app de relógio, senhor."
        ctx.startActivity(i)
        return "alarme definido para " + String.format("%02d:%02d", h, m) + ", senhor."
    }

    private fun lanterna(ctx: Context, args: JSONObject): String {
        val ligar = args.optString("acao") != "desligar"
        val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val id = cm.cameraIdList.firstOrNull { cm.getCameraCharacteristics(it).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true }
            ?: return "esse aparelho não tem flash, senhor."
        cm.setTorchMode(id, ligar)
        return "lanterna " + (if (ligar) "ligada" else "desligada") + ", senhor."
    }

    private fun abrirApp(ctx: Context, args: JSONObject): String {
        val nome = args.optString("nome").trim()
        if (nome.isEmpty()) return "diga o nome do app, senhor."
        val alvo = normalizar(nome)
        val pm = ctx.packageManager

        // 1) apelidos brasileiros comuns → pacote oficial (o Gmail nunca contém 'email'!)
        for ((apelido, pacote) in APELIDOS_APPS) {
            if (alvo == apelido || alvo.contains(apelido)) {
                val i = pm.getLaunchIntentForPackage(pacote)
                if (i != null) {
                    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    ctx.startActivity(i)
                    return "abrindo " + pm.getApplicationLabel(pm.getApplicationInfo(pacote, 0)) + ", senhor."
                }
            }
        }

        // 2) busca inteligente nos apps instalados (rótulo e pacote, sem acento, nos dois sentidos)
        data class Cand(val rotulo: String, val pacote: String, val score: Int)
        val candidatos = mutableListOf<Cand>()
        for (pi in pm.getInstalledApplications(0)) {
            val rotulo = normalizar(pm.getApplicationLabel(pi).toString())
            val pacote = pi.packageName.lowercase()
            val score = when {
                rotulo == alvo || pacote == alvo -> 100
                rotulo.contains(alvo) || pacote.contains(alvo) -> 70
                alvo.contains(rotulo) && rotulo.length >= 3 -> 50
                else -> -1
            }
            if (score > 0) candidatos.add(Cand(rotulo, pi.packageName, score))
        }
        if (candidatos.isNotEmpty()) {
            val melhor = candidatos.sortedWith(
                compareByDescending<Cand> { it.score }.thenBy { it.rotulo.length }
            ).first()
            val i = pm.getLaunchIntentForPackage(melhor.pacote)
                ?: return "'" + melhor.rotulo + "' não tem tela pra abrir, senhor."
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(i)
            return "abrindo " + melhor.rotulo + ", senhor."
        }
        return "não achei app chamado '" + nome + "', senhor. Tente o nome que aparece na gaveta de apps."
    }

    /** Minúsculas e sem acento: 'Câmera' → 'camera'. */
    private fun normalizar(t: String): String =
        java.text.Normalizer.normalize(t.lowercase(), java.text.Normalizer.Form.NFD)
            .replace("\p{Mn}+".toRegex(), "")
            .trim()

    /** Apelidos que o povo usa → pacote oficial (buscados na ordem). */
    private val APELIDOS_APPS: List<Pair<String, String>> = listOf(
        "email" to "com.google.android.gm",
        "gmail" to "com.google.android.gm",
        "e-mail" to "com.google.android.gm",
        "whatsapp" to "com.whatsapp",
        "zap" to "com.whatsapp",
        "whats" to "com.whatsapp",
        "youtube" to "com.google.android.youtube",
        "instagram" to "com.instagram.android",
        "insta" to "com.instagram.android",
        "facebook" to "com.katana",
        "navegador" to "com.android.chrome",
        "chrome" to "com.android.chrome",
        "internet" to "com.android.chrome",
        "maps" to "com.google.android.apps.maps",
        "mapa" to "com.google.android.apps.maps",
        "gps" to "com.google.android.apps.maps",
        "waze" to "com.waze",
        "agenda" to "com.google.android.calendar",
        "calendario" to "com.google.android.calendar",
        "relogio" to "com.google.android.deskclock",
        "alarme" to "com.google.android.deskclock",
        "calculadora" to "com.google.android.calculator",
        "telefone" to "com.android.dialer",
        "ligacoes" to "com.android.dialer",
        "discador" to "com.android.dialer",
        "contatos" to "com.android.contacts",
        "play store" to "com.android.vending",
        "playstore" to "com.android.vending",
        "fotos" to "com.google.android.apps.photos",
        "galeria" to "com.google.android.apps.photos",
        "spotify" to "com.spotify.music",
        "mensagens" to "com.google.android.apps.messaging",
        "sms" to "com.google.android.apps.messaging",
        "configuracoes" to "com.android.settings",
        "ajustes" to "com.android.settings",
        "drive" to "com.google.android.apps.docs",
        "tiktok" to "com.zhiliaoapp.musically"
    )

    private fun definirTimer(ctx: Context, args: JSONObject): String {
        val min = args.optInt("minutos", -1)
        if (min < 1 || min > 720) return "me diga os minutos, senhor, ex: 'timer de 10 minutos'."
        val i = Intent(AlarmClock.ACTION_SET_TIMER).apply {
            putExtra(AlarmClock.EXTRA_LENGTH, min)
            putExtra(AlarmClock.EXTRA_MESSAGE, args.optString("rotulo").ifBlank { "JARVIS" })
            putExtra(AlarmClock.EXTRA_SKIP_UI, true)
        }.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        if (i.resolveActivity(ctx.packageManager) == null) return "não achei o app de relógio, senhor."
        ctx.startActivity(i)
        return "timer de " + min + " minutos definido, senhor."
    }

    private fun pesquisarWeb(ctx: Context, args: JSONObject): String {
        val q = args.optString("consulta")
        if (q.isBlank()) return "o que pesquisar, senhor?"
        ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=" + URLEncoder.encode(q, "UTF-8"))).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        return "abrindo a pesquisa de '" + q + "', senhor."
    }

    private fun listarMemorias(ctx: Context, args: JSONObject): String {
        val n = args.optInt("quantidade", 10).coerceIn(1, 20)
        val ms = JarvisMemory.recent(ctx, n)
        return if (ms.isEmpty()) "ainda não guardei nenhum fato, senhor — me peça pra lembrar de algo."
        else "o que sei do senhor:\n- " + ms.joinToString("\n- ")
    }

    // ---------- v4.7.3: modo mesa, agenda e email ----------

    private fun abrirModoMesa(ctx: Context): String = try {
        ctx.startActivity(Intent(ctx, DeskModeActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        "modo mesa aberto, senhor — o painel holográfico assume a tela."
    } catch (e: Exception) {
        "falha ao abrir o modo mesa: ${e.message ?: "sem detalhes"}"
    }

    private fun criarLembrete(ctx: Context, args: JSONObject): String = try {
        val inicio = args.optLong("inicio_ms", System.currentTimeMillis())
        val dur = args.optInt("minutos", 60)
        val intent = Intent(Intent.ACTION_INSERT)
            .setData(CalendarContract.Events.CONTENT_URI)
            .putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, inicio)
            .putExtra(CalendarContract.EXTRA_EVENT_END_TIME, inicio + dur * 60_000L)
            .putExtra(CalendarContract.Events.TITLE, args.optString("titulo"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)
        "abri a agenda com o lembrete '" + args.optString("titulo") + "' pronto, senhor — só tocar em salvar."
    } catch (e: Exception) {
        "falha ao abrir a agenda: ${e.message ?: "sem detalhes"}"
    }

    private fun enviarEmail(ctx: Context, args: JSONObject): String = try {
        val intent = Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:" + Uri.encode(args.optString("para"))))
            .putExtra(Intent.EXTRA_SUBJECT, args.optString("assunto"))
            .putExtra(Intent.EXTRA_TEXT, args.optString("corpo"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try {
            ctx.startActivity(intent)
        } catch (e: Exception) {
            // sem app de email associado ao mailto: oferece o seletor do sistema
            ctx.startActivity(Intent.createChooser(intent, "Escolha o app de email").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        "email pronto pro senhor conferir e enviar."
    } catch (e: Exception) {
        "não achei app de email, senhor — tente pedir 'abrir email' que eu abro o Gmail."
    }

}
