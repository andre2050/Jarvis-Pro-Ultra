package com.andre.jarvisultra

/** Memória curta das notificações capturadas (últimas 50). */
object JarvisNotificationStore {
    private val items = mutableListOf<String>()

    fun add(line: String) {
        synchronized(items) {
            items.add(0, line)
            if (items.size > 50) items.removeAt(items.size - 1)
        }
    }

    fun recent(n: Int): List<String> = synchronized(items) { items.take(n).toList() }
}
