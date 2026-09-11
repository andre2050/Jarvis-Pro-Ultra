package com.andre.jarvisultra

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import org.json.JSONArray

data class ChatMessage(val role: String, val text: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JarvisApp() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()

    var messages by remember { mutableStateOf(listOf(ChatMessage("model", "Sistemas online. Bom te ver, senhor — em que posso ajudar?"))) }
    var input by remember { mutableStateOf("") }
    var isThinking by remember { mutableStateOf(false) }
    var isSpeaking by remember { mutableStateOf(false) }
    var apiKeyInput by remember { mutableStateOf("") }
    var apiKeySaved by remember { mutableStateOf(SettingsStore.hasApiKey(ctx)) }
    var showSettings by remember { mutableStateOf(!apiKeySaved) }
    var updateInfo by remember { mutableStateOf<String?>(null) }

    val voice = remember {
        JarvisVoice(ctx).also { v ->
            v.listener = object : JarvisVoice.Listener {
                override fun onSpeakingChanged(speaking: Boolean) { isSpeaking = speaking }
            }
        }
    }
    DisposableEffect(Unit) { onDispose { voice.shutdown() } }

    val history = remember { JSONArray() }
    val listState = rememberLazyListState()

    val stt = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) {
            val text = res.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            if (!text.isNullOrBlank()) input = text
        }
    }

    fun send() {
        val msg = input.trim()
        if (msg.isEmpty() || isThinking || !apiKeySaved) return
        input = ""
        messages = messages + ChatMessage("user", msg) + ChatMessage("model", "…")
        isThinking = true
        scope.launch {
            val key = SettingsStore.getApiKey(ctx)
            val result = try {
                JarvisBrain.process(ctx, key, history, msg)
            } catch (e: Exception) {
                JarvisBrain.TurnResult(e.message ?: "erro inesperado", history, emptyList())
            }
            isThinking = false
            val reply = result.reply.ifBlank { "Às ordens, senhor." }
            messages = messages.dropLast(1) + ChatMessage("model", reply)
            if (!reply.startsWith("⚠️")) voice.speak(reply)
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            HologramFace(
                modifier = Modifier
                    .padding(top = 8.dp, bottom = 4.dp)
                    .size(150.dp),
                isSpeaking = isSpeaking,
                isThinking = isThinking
            )
            Row(Modifier.align(Alignment.TopEnd).padding(10.dp)) {
                IconButton(onClick = {
                    scope.launch {
                        updateInfo = try { Updater.check() } catch (e: Exception) { e.message }
                    }
                }) {
                    Icon(Icons.Default.Refresh, contentDescription = "Verificar atualização", tint = CyanDim)
                }
                IconButton(onClick = {
                    apiKeyInput = SettingsStore.getApiKey(ctx)
                    showSettings = true
                }) {
                    Icon(Icons.Default.Settings, contentDescription = "Configurações", tint = CyanDim)
                }
            }
        }
        Text(
            text = when {
                isThinking -> "processando…"
                isSpeaking -> "falando…"
                else -> "J.A.R.V.I.S PRO ULTRA v" + JarvisBrain.APP_VERSION + " — online"
            },
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(bottom = 6.dp),
            color = Cyan.copy(alpha = 0.75f),
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace
        )

        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(messages) { m ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = if (m.role == "user") Arrangement.End else Arrangement.Start
                ) {
                    Surface(
                        color = if (m.role == "user") Cyan.copy(alpha = 0.14f) else MaterialTheme.colorScheme.surface,
                        contentColor = MaterialTheme.colorScheme.onSurface,
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, HoloLine),
                        modifier = Modifier.widthIn(max = 320.dp)
                    ) {
                        Text(m.text, Modifier.padding(10.dp), fontSize = 14.sp, lineHeight = 19.sp)
                    }
                }
            }
        }

        Surface(
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 2.dp,
            modifier = Modifier.fillMaxWidth().padding(top = 6.dp)
        ) {
            Row(
                Modifier.padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = {
                    val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                        putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
                        putExtra(RecognizerIntent.EXTRA_PROMPT, "Fale com o JARVIS")
                    }
                    stt.launch(intent)
                }) {
                    Icon(Icons.Default.Mic, contentDescription = "Falar", tint = Cyan)
                }

                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("Mande uma ordem, senhor…", fontSize = 14.sp) },
                    singleLine = true,
                    shape = RoundedCornerShape(14.dp)
                )

                Spacer(Modifier.width(6.dp))
                FilledIconButton(onClick = { send() }, enabled = input.isNotBlank() && !isThinking) {
                    Icon(Icons.Default.KeyboardArrowUp, contentDescription = "Enviar")
                }
            }
        }
    }

    if (showSettings) {
        AlertDialog(
            onDismissRequest = { if (apiKeySaved) showSettings = false },
            title = { Text("Configuração do JARVIS") },
            text = {
                Column {
                    Text("Cole sua chave do Google AI Studio (fica só neste dispositivo):", fontSize = 13.sp)
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = apiKeyInput,
                        onValueChange = { apiKeyInput = it },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("AIza…") }
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Pegue em: aistudio.google.com/app/api-key",
                        fontSize = 11.sp,
                        color = CyanDim
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    SettingsStore.setApiKey(ctx, apiKeyInput)
                    apiKeySaved = SettingsStore.hasApiKey(ctx)
                    showSettings = false
                }) { Text("Salvar") }
            },
            dismissButton = {
                if (apiKeySaved) {
                    TextButton(onClick = { showSettings = false }) { Text("Fechar") }
                }
            }
        )
    }

    updateInfo?.let { info ->
        AlertDialog(
            onDismissRequest = { updateInfo = null },
            title = { Text("Atualização") },
            text = { Text(info) },
            confirmButton = {
                TextButton(onClick = {
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(Updater.RELEASES_URL)))
                    updateInfo = null
                }) { Text("Abrir releases") }
            },
            dismissButton = {
                TextButton(onClick = { updateInfo = null }) { Text("Depois") }
            }
        )
    }
}
