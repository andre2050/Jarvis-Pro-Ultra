package com.andre.jarvisultra

import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
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
import androidx.compose.material.icons.filled.Phone
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
import org.json.JSONObject

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
    var testResult by remember { mutableStateOf<String?>(null) }
    var suggestion by remember { mutableStateOf<JarvisMemory.Suggestion?>(null) }
    var handsFree by remember { mutableStateOf("off") }
    var voskSession by remember { mutableStateOf<JarvisVosk.Session?>(null) }
    val mainHandler = remember { android.os.Handler(android.os.Looper.getMainLooper()) }

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

    LaunchedEffect(Unit) {
        suggestion = try { JarvisMemory.suggest(ctx) } catch (e: Exception) { null }
    }

    LaunchedEffect(apiKeySaved) {
        if (apiKeySaved) {
            val pedidas = mutableListOf<String>()
            for (p in listOf(
                android.Manifest.permission.CALL_PHONE,
                android.Manifest.permission.READ_CONTACTS,
                android.Manifest.permission.SEND_SMS,
                android.Manifest.permission.READ_SMS
            )) {
                if (ContextCompat.checkSelfPermission(ctx, p) != PackageManager.PERMISSION_GRANTED) pedidas.add(p)
            }
            if (pedidas.isNotEmpty()) ActivityCompat.requestPermissions(ctx as Activity, pedidas.toTypedArray(), 77)
        }
    }

    val stt = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) {
            val text = res.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            if (!text.isNullOrBlank()) input = text
        }
    }

    fun send(forced: String? = null) {
        val msg = (forced ?: input).trim()
        suggestion = null
        if (msg.isEmpty() || isThinking) return
        if (!apiKeySaved) {
            messages = messages + ChatMessage("model", "Ainda não tenho a chave do Gemini, senhor — toque na engrenagem no topo, cole a chave e salve. Aí sim, às ordens.")
            return
        }
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

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        HudBackground(Modifier.fillMaxSize(), isThinking = isThinking, isListening = (handsFree == "on"))
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            HologramFace(
                modifier = Modifier
                    .padding(top = 8.dp, bottom = 4.dp)
                    .size(150.dp),
                isSpeaking = isSpeaking,
                isThinking = isThinking,
                isListening = (handsFree == "on")
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
                handsFree == "on" -> "escutando — fale \"jarvis\""
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
                val isUser = m.role == "user"
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
                ) {
                    Text(
                        if (isUser) "SENHOR" else "J.A.R.V.I.S",
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        color = if (isUser) CyanDim else Cyan.copy(alpha = 0.75f),
                        modifier = Modifier.padding(start = 4.dp, end = 4.dp, bottom = 2.dp)
                    )
                    Surface(
                        color = if (isUser) Cyan.copy(alpha = 0.14f) else MaterialTheme.colorScheme.surface,
                        contentColor = MaterialTheme.colorScheme.onSurface,
                        shape = RoundedCornerShape(
                            topStart = if (isUser) 12.dp else 3.dp,
                            topEnd = if (isUser) 3.dp else 12.dp,
                            bottomStart = 12.dp,
                            bottomEnd = 12.dp
                        ),
                        border = BorderStroke(1.dp, if (isUser) CyanDim else HoloLine),
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
            if (handsFree != "off" && handsFree != "on") {
                Text(handsFree, Modifier.padding(start = 12.dp, top = 4.dp), fontSize = 11.sp, color = CyanDim)
            }
            suggestion?.let { s ->
                TextButton(
                    onClick = { suggestion = null; send(s.message) },
                    modifier = Modifier.padding(start = 6.dp, top = 2.dp)
                ) {
                    Text(s.label, fontSize = 12.sp, color = CyanDim)
                }
            }
            Row(
                Modifier.padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = {
                    if (handsFree == "on") {
                        voskSession?.stop(); voskSession = null; handsFree = "off"
                    } else if (ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                        ActivityCompat.requestPermissions(ctx as Activity, arrayOf(android.Manifest.permission.RECORD_AUDIO), 78)
                    } else {
                        fun startSession() {
                            try {
                                voskSession = JarvisVosk.Session(ctx,
                                    onCommand = { txt -> mainHandler.post { send(txt) } },
                                    onWake = { mainHandler.post { voice.speak("Pois não, senhor?") } },
                                    onState = { s -> mainHandler.post { handsFree = s } })
                                voskSession?.start()
                                handsFree = "on"
                            } catch (e: Exception) { handsFree = "erro: " + (e.message ?: "falha ao iniciar") }
                        }
                        if (!JarvisVosk.hasModel(ctx)) {
                            handsFree = "baixando pacote de voz..."
                            Thread {
                                val err = JarvisVosk.ensureModel(ctx) { msg -> mainHandler.post { handsFree = msg } }
                                mainHandler.post { if (err == null) startSession() else handsFree = "falha: " + err }
                            }.start()
                        } else startSession()
                    }
                }) {
                    Icon(Icons.Default.Phone, contentDescription = "Mãos livres",
                        tint = if (handsFree == "on") Cyan else CyanDim)
                }

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
    }

    if (showSettings) {
        AlertDialog(
            onDismissRequest = { if (apiKeySaved) showSettings = false },
            title = { Text("Configuração do JARVIS (v" + JarvisBrain.APP_VERSION + ")") },
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
                    Spacer(Modifier.height(8.dp))
                    TextButton(onClick = {
                        scope.launch {
                            testResult = "testando…"
                            testResult = try {
                                val contents = JSONArray()
                                    .put(JSONObject().put("role", "user")
                                        .put("parts", JSONArray().put(JSONObject().put("text", "oi"))))
                                val r = GeminiClient.turn(apiKeyInput.trim(), "Responda apenas: ok", contents, null)
                                "\u2705 Chave OK! O Gemini (" + r.model + ") respondeu."
                            } catch (e: Exception) { "\u274c " + (e.message ?: "falhou") }
                        }
                    }) { Text("Testar chave") }
                    testResult?.let { tr ->
                        Text(tr, fontSize = 12.sp, color = Cyan)
                    }
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
