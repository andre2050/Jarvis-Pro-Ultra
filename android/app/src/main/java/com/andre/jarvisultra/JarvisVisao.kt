package com.andre.jarvisultra

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

/**
 * VISÃO COMPUTACIONAL (v4.5.0) — os olhos do JARVIS.
 * Fluxo: a tool ver_camera (ou o botão de câmera) abre a câmera do sistema;
 * a foto capturada é reduzida, comprimida em JPEG e enviada ao Gemini como
 * inline_data (multimodal) — o JARVIS vê de verdade o que o senhor apontou.
 */
object JarvisVisao {

    /** Callback registrado pela UI: abre a câmera com a pergunta pendente e a câmera escolhida (frontal/traseira). */
    @Volatile var onCaptureRequest: ((pergunta: String?, camera: String?) -> Unit)? = null

    fun declarations(): JSONArray {
        val ver = JSONObject()
            .put(
                "name", "ver_camera"
            )
            .put(
                "description",
                "VISÃO COMPUTACIONAL: abre a câmera para o JARVIS VER o mundo real. Use SEMPRE que o senhor " +
                    "pedir para ver/olhar/fotografar algo, ler um texto físico (etiqueta, conta, papel), " +
                    "identificar um objeto ou perguntar 'o que é isso?'. Depois da foto, você receberá a imagem " +
                    "na conversa e deverá analisá-la (descrever, transcrever textos, responder a pergunta)."
            )
            .put(
                "parameters",
                JSONObject()
                    .put("type", "object")
                    .put(
                        "properties",
                        JSONObject().put(
                            "pergunta",
                            JSONObject()
                                .put("type", "string")
                                .put(
                                    "description",
                                    "O que o senhor quer saber sobre a imagem, ex: 'leia o texto', 'o que é isso?'. " +
                                        "Se não disser nada, apenas descreva o que vê de forma útil."
                                )
                        )
                        .put(
                            "camera",
                            JSONObject()
                                .put("type", "string")
                                .put("enum", JSONArray().put("frontal").put("traseira"))
                                .put(
                                    "description",
                                    "Qual câmera usar: 'frontal' (selfie — para o JARVIS olhar o senhor ou o que está " +
                                        "atrás/em volta do celular) ou 'traseira' (câmera principal, padrão). " +
                                        "Se o senhor disser 'se olhe', 'olhe pra mim', use frontal."
                                )
                        )
                    )
            )
        return JSONArray().put(ver)
    }

    /** Executa a tool de visão. Retorna null se não for tool deste módulo. */
    fun execute(ctx: Context, name: String, args: JSONObject): String? {
        if (name == "ver_camera") {
            val pergunta = args.optString("pergunta").takeIf { it.isNotBlank() }
            val camera = args.optString("camera").takeIf { it.isNotBlank() }
            val cb = onCaptureRequest
                ?: return "câmera indisponível no momento, senhor — tente pelo botão de foto na barra de comando."
            cb(pergunta, camera)
            return "câmera aberta, senhor. Aponte para o alvo e toque no botão de foto — assim que capturar, eu analiso."
        }
        return null
    }

    /**
     * Decodifica a foto, reduz para no máximo 1024px do maior lado, comprime em JPEG
     * e devolve (base64, mime) prontos para inline_data no Gemini. Null se falhar.
     */
    fun codificarParaGemini(ctx: Context, uri: Uri, maxDim: Int = 1024): Pair<String, String>? {
        var bmp: Bitmap? = null
        return try {
            ctx.contentResolver.openInputStream(uri)?.use { ins ->
                BitmapFactory.decodeStream(ins)
            }?.let { original ->
                bmp = original
                val maior = maxOf(original.width, original.height)
                val small =
                    if (maior > maxDim) {
                        val scale = maxDim.toFloat() / maior
                        Bitmap.createScaledBitmap(
                            original,
                            (original.width * scale).toInt().coerceAtLeast(1),
                            (original.height * scale).toInt().coerceAtLeast(1),
                            true
                        )
                    } else original
                val bos = ByteArrayOutputStream()
                small.compress(Bitmap.CompressFormat.JPEG, 82, bos)
                val b64 = Base64.encodeToString(bos.toByteArray(), Base64.NO_WRAP)
                if (small !== original) original.recycle()
                small.recycle()
                Pair(b64, "image/jpeg")
            }
        } catch (e: Exception) {
            bmp?.recycle()
            null
        }
    }
}
