package com.andre.jarvisultra

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

/**
 * Leitor de notificações (v2.1.0): captura mensagens que chegam no WhatsApp e
 * no SMS pra o JARVIS saber delas. O usuário autoriza uma vez nas configurações
 * de acesso a notificações do Android.
 */
class JarvisNotificationListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val pkg = sbn.packageName
        if (pkg != "com.whatsapp" && pkg != "com.whatsapp.w4b" &&
            pkg != "com.google.android.apps.messaging" && pkg != "com.android.mms") return
        val extras = sbn.notification?.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: "Mensagem"
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: return
        if (text.isBlank()) return
        JarvisNotificationStore.add(title + ": " + text)
    }
}
