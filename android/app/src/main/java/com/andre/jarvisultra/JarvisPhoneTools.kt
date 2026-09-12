package com.andre.jarvisultra

import android.provider.AlarmClock
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.net.Uri
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

        r.put(obj("abrir_app",
            "Abre um app instalado pelo nome, ex: 'abre o YouTube'.",
            JSONObject().put("nome", JSONObject().put("type", "string").put("description", "nome do app")),
            JSONArray().put("nome")))

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
        val nome = args.optString("nome").trim().lowercase()
        val pm = ctx.packageManager
        val alvo = pm.getInstalledApplications(0).firstOrNull {
            pm.getApplicationLabel(it).toString().lowercase().contains(nome) ||
                it.packageName.lowercase().contains(nome)
        } ?: return "não achei app chamado '" + nome + "', senhor."
        val i = pm.getLaunchIntentForPackage(alvo.packageName)
            ?: return "'" + pm.getApplicationLabel(alvo) + "' não tem tela pra abrir, senhor."
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(i)
        return "abrindo " + pm.getApplicationLabel(alvo) + ", senhor."
    }
}
