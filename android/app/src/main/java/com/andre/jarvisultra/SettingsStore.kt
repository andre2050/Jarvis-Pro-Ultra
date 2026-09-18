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
    private const val KEY_THEME = "hud_theme"
    private const val KEY_USER_NAME = "user_name"
    private const val KEY_ASSISTANT_NAME = "assistant_name"
    private const val KEY_AVATAR_INTRO = "v48_avatar_intro"

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

    /** Tema do holograma: "avatar" (rosto com dublagem, v4.8.0), "radar" ou "arc". */
    fun getTheme(ctx: Context): String {
        val t = prefs(ctx).getString(KEY_THEME, "avatar") ?: "avatar"
        return if (t in listOf("avatar", "radar", "arc")) t else "radar"
    }

    fun setTheme(ctx: Context, tema: String) {
        val t = if (tema in listOf("avatar", "radar", "arc")) tema else "radar"
        prefs(ctx).edit().putString(KEY_THEME, t).apply()
    }

    /** Personalização (v4.8.0): nome do usuário e do assistente. */
    fun getUserName(ctx: Context): String = prefs(ctx).getString(KEY_USER_NAME, "") ?: ""

    fun setUserName(ctx: Context, nome: String) {
        prefs(ctx).edit().putString(KEY_USER_NAME, nome.trim()).apply()
    }

    fun getAssistantName(ctx: Context): String = prefs(ctx).getString(KEY_ASSISTANT_NAME, "JARVIS") ?: "JARVIS"

    fun setAssistantName(ctx: Context, nome: String) {
        prefs(ctx).edit().putString(KEY_ASSISTANT_NAME, nome.trim().ifBlank { "JARVIS" }).apply()
    }

    /** Migração única v4.8.0: apresenta o avatar a quem usava o radar. */
    fun avatarIntroDone(ctx: Context): Boolean = prefs(ctx).getBoolean(KEY_AVATAR_INTRO, false)

    fun markAvatarIntro(ctx: Context) {
        prefs(ctx).edit().putBoolean(KEY_AVATAR_INTRO, true).apply()
    }

    fun hasApiKey(ctx: Context): Boolean = getApiKey(ctx).length >= 20
}
