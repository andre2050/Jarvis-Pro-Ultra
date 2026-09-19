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
        tts = try {
            TextToSpeech(ctx.applicationContext) { status ->
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
        } catch (_: Exception) { null }   // sem voz é melhor que sem app
    }

    fun setEnabled(v: Boolean) { enabled = v }
    fun setTtsRate(r: Float) { rate = r; tts?.setSpeechRate(r) }

    fun speak(text: String) {
        if (!enabled || text.isBlank()) return
        val id = "jarvis-${System.nanoTime()}"
        pending[id] = text
        speakNow(text, id)
    }

    /** v4.9.0: fala imediata (briefing matinal) — ignora o toggle de voz do chat. */
    fun speakNow(text: String) {
        if (text.isBlank()) return
        val id = "jarvis-${System.nanoTime()}"
        pending[id] = text
        speakNow(text, id)
    }

    val isSpeaking: Boolean get() = tts?.isSpeaking == true || pending.isNotEmpty()

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
