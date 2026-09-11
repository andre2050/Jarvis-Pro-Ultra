package com.andre.jarvisultra

import android.content.Context

/**
 * Configuração central do JARVIS no Android (equivalente ao config/settings.json do desktop).
 * A chave do Gemini fica só no dispositivo — nunca sai dele, nunca vai pro GitHub.
 */
object SettingsStore {
    private const val PREFS = "jarvis_settings"
    private const val KEY_API = "gemini_api_key"
    private const val KEY_VOICE = "voice_enabled"
    private const val KEY_TTS_RATE = "tts_rate"

    fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun getApiKey(ctx: Context): String = prefs(ctx).getString(KEY_API, "") ?: ""

    fun setApiKey(ctx: Context, key: String) {
        prefs(ctx).edit().putString(KEY_API, key.trim()).apply()
    }

    fun isVoiceEnabled(ctx: Context): Boolean = prefs(ctx).getBoolean(KEY_VOICE, true)

    fun setVoiceEnabled(ctx: Context, v: Boolean) {
        prefs(ctx).edit().putBoolean(KEY_VOICE, v).apply()
    }

    fun getTtsRate(ctx: Context): Float = prefs(ctx).getFloat(KEY_TTS_RATE, 1.0f)

    fun setTtsRate(ctx: Context, rate: Float) {
        prefs(ctx).edit().putFloat(KEY_TTS_RATE, rate).apply()
    }

    fun hasApiKey(ctx: Context): Boolean = getApiKey(ctx).length >= 20
}
