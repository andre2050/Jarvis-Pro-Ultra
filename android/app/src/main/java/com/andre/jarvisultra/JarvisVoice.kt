package com.andre.jarvisultra

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * Voz do JARVIS: TextToSpeech nativo do Android em pt-BR.
 * O listener de utterance informa à UI quando ele está falando —
 * é isso que anima a boca do holograma em sincronia com a fala.
 */
class JarvisVoice(ctx: Context) {
    interface Listener { fun onSpeakingChanged(speaking: Boolean) }

    private var tts: TextToSpeech? = null
    var listener: Listener? = null
    private var rate: Float = SettingsStore.getTtsRate(ctx)
    private var enabled: Boolean = SettingsStore.isVoiceEnabled(ctx)
    private val pending = ConcurrentHashMap<String, String>()

    init {
        tts = TextToSpeech(ctx.applicationContext) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("pt", "BR")
                tts?.setSpeechRate(rate)
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) { listener?.onSpeakingChanged(true) }
                    override fun onDone(utteranceId: String?) {
                        pending.remove(utteranceId)
                        if (pending.isEmpty()) listener?.onSpeakingChanged(false)
                    }
                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {
                        pending.remove(utteranceId)
                        if (pending.isEmpty()) listener?.onSpeakingChanged(false)
                    }
                })
                // fala tudo que foi pedida antes da inicialização terminar
                pending.forEach { (id, text) -> speakNow(text, id) }
            }
        }
    }

    fun setEnabled(v: Boolean) { enabled = v }
    fun setTtsRate(r: Float) { rate = r; tts?.setSpeechRate(r) }

    fun speak(text: String) {
        if (!enabled || text.isBlank()) return
        val id = "jarvis-${System.nanoTime()}"
        pending[id] = text
        speakNow(text, id)
    }

    private fun speakNow(text: String, id: String) {
        val t = tts ?: return
        if (t.isSpeaking) {
            t.speak(text, TextToSpeech.QUEUE_ADD, null, id)
        } else {
            t.speak(text, TextToSpeech.QUEUE_FLUSH, null, id)
        }
    }

    fun shutdown() { tts?.stop(); tts?.shutdown(); tts = null }
}
