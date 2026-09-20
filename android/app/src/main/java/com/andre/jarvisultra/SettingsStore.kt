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
    private const val KEY_WAKE_24H = "wake24h_enabled"
    private const val KEY_AVISO_PRESENCA = "aviso_presenca"
    private const val KEY_BRAIN_MODE = "brain_mode"
    private const val KEY_BRIEFING_ON = "briefing_enabled"
    private const val KEY_BRIEFING_HORA = "briefing_hora"

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

    /**
     * v4.9.3: UMA ÚNICA SKIN — o Busto Holográfico da referência do senhor.
     * Qualquer tema antigo (avatar/radar/arc/buster) migra automaticamente.
     */
    fun getTheme(ctx: Context): String {
        val t = prefs(ctx).getString(KEY_THEME, "busto") ?: "busto"
        if (t != "busto") prefs(ctx).edit().putString(KEY_THEME, "busto").apply()
        return "busto"
    }

    fun setTheme(ctx: Context, tema: String) {
        prefs(ctx).edit().putString(KEY_THEME, "busto").apply()
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

    // ---- Presença 24h (v4.9.0): wake word com o app em segundo plano ----
    fun getWake24h(ctx: Context): Boolean = prefs(ctx).getBoolean(KEY_WAKE_24H, false)

    fun setWake24h(ctx: Context, v: Boolean) {
        prefs(ctx).edit().putBoolean(KEY_WAKE_24H, v).apply()
    }

    /** v4.9.9: motivo de a presença não ter conseguido ligar (Android 14 exige
     * o app visível na tela pra iniciar serviço de microfone). Null = sem pendência. */
    fun getAvisoPresenca(ctx: Context): String? = prefs(ctx).getString(KEY_AVISO_PRESENCA, null)
    fun setAvisoPresenca(ctx: Context, msg: String?) {
        prefs(ctx).edit().putString(KEY_AVISO_PRESENCA, msg).apply()
    }

    // ---- v4.10.0: cérebro local (offline) ou nuvem (Gemini) ----
    fun getBrainMode(ctx: Context): String = prefs(ctx).getString(KEY_BRAIN_MODE, "cloud") ?: "cloud"
    fun setBrainMode(ctx: Context, v: String) {
        prefs(ctx).edit().putString(KEY_BRAIN_MODE, v).apply()
    }

    // ---- Briefing matinal (v4.9.0) ----
    fun getBriefingOn(ctx: Context): Boolean = prefs(ctx).getBoolean(KEY_BRIEFING_ON, false)

    fun setBriefingOn(ctx: Context, v: Boolean) {
        prefs(ctx).edit().putBoolean(KEY_BRIEFING_ON, v).apply()
    }

    /** Horário no formato "HH:mm", padrão 08:00. */
    fun getBriefingHora(ctx: Context): String = prefs(ctx).getString(KEY_BRIEFING_HORA, "08:00") ?: "08:00"

    fun setBriefingHora(ctx: Context, hora: String) {
        prefs(ctx).edit().putString(KEY_BRIEFING_HORA, hora).apply()
    }
}
