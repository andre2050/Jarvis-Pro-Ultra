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
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.io.File
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
    var voiceWork by remember { mutableStateOf<String?>(null) }
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
                android.Manifest.permission.READ_SMS,
                android.Manifest.permission.ACCESS_FINE_LOCATION
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

    Box(
        Modifier.fillMaxSize().background(
            Brush.verticalGradient(listOf(Color(0xFF150404), Color(0xFF0A0303), Color(0xFF020000)))
        )
    ) {
        Box(
            Modifier.fillMaxWidth().height(320.dp).background(
                Brush.radialGradient(listOf(Cyan.copy(alpha = 0.07f), Color(0x00000000)))
            )
        )
        HudBackground(Modifier.fillMaxSize(), isThinking = isThinking, isListening = (handsFree == "on"))
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            ArcReactorHud(
                modifier = Modifier
                    .padding(top = 8.dp, bottom = 4.dp)
                    .size(190.dp),
                ctx = ctx,
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
        Row(
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(bottom = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            val dotPulse by rememberInfiniteTransition(label = "dot")
                .animateFloat(0f, 1f, infiniteRepeatable(tween(1300, easing = LinearEasing)), label = "dp")
            Box(
                Modifier
                    .size(7.dp)
                    .graphicsLayer { alpha = 0.35f + 0.65f * dotPulse }
                    .background(Cyan, CircleShape)
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = when {
                    isThinking -> "processando…"
                    isSpeaking -> "falando…"
                    handsFree == "on" -> "escutando — fale \"jarvis\""
                    else -> "J.A.R.V.I.S PRO ULTRA v" + JarvisBrain.APP_VERSION + " — online"
                },
                color = Cyan.copy(alpha = 0.75f),
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 1.5.sp
            )
        }

        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(messages) { m ->
                val isUser = m.role == "user"
                var shown by remember { mutableStateOf(false) }
                LaunchedEffect(Unit) { shown = true }
                val animAlpha by animateFloatAsState(if (shown) 1f else 0f, tween(280), label = "a")
                val animDy by animateFloatAsState(if (shown) 0f else 22f, tween(280), label = "dy")
                Column(
                    modifier = Modifier.fillMaxWidth().graphicsLayer {
                        alpha = animAlpha
                        translationY = animDy
                    },
                    horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
                ) {
                    Text(
                        if (isUser) "SENHOR" else "J.A.R.V.I.S",
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        color = if (isUser) CyanDim else Cyan.copy(alpha = 0.75f),
                        modifier = Modifier.padding(start = 4.dp, end = 4.dp, bottom = 2.dp)
                    )
                    val shape = RoundedCornerShape(
                        topStart = if (isUser) 14.dp else 4.dp,
                        topEnd = if (isUser) 4.dp else 14.dp,
                        bottomStart = 14.dp,
                        bottomEnd = 14.dp
                    )
                    Surface(
                        color = if (isUser) Cyan.copy(alpha = 0.12f) else Color(0xF2190606),
                        contentColor = MaterialTheme.colorScheme.onSurface,
                        shape = shape,
                        modifier = Modifier
                            .widthIn(max = 320.dp)
                            .border(
                                width = 1.dp,
                                brush = if (isUser)
                                    Brush.linearGradient(listOf(CyanDim, Cyan.copy(alpha = 0.15f)))
                                else
                                    Brush.linearGradient(listOf(Cyan.copy(alpha = 0.20f), HoloLine)),
                                shape = shape
                            )
                    ) {
                        Text(
                            m.text,
                            Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                            fontSize = 14.sp,
                            lineHeight = 19.sp
                        )
                    }
                }
            }
        }

        Surface(
            color = Color(0xD9130404),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 6.dp)
                .border(
                    1.dp,
                    Brush.horizontalGradient(listOf(HoloLine, Cyan.copy(alpha = 0.20f), HoloLine)),
                    RectangleShape
                )
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
                    placeholder = { Text("Mande uma ordem, senhor…", fontSize = 14.sp, color = Color(0xFF8A6060)) },
                    singleLine = true,
                    shape = RoundedCornerShape(18.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Cyan,
                        unfocusedBorderColor = HoloLine,
                        focusedTextColor = Color(0xFFF3E5E0),
                        unfocusedTextColor = Color(0xFFF3E5E0),
                        cursorColor = Cyan
                    )
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
            title = { Text("Configurações — v" + JarvisBrain.APP_VERSION) },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState())) {
                    Text("CHAVE DO GEMINI", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
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
                    }) { Text("Testar chave", fontSize = 12.sp) }
                    testResult?.let { tr ->
                        Text(tr, fontSize = 12.sp, color = Cyan)
                    }

                    Spacer(Modifier.height(16.dp))
                    Text("MICROFONE \ud83c\udf99\ufe0f", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
                    val vozPronta = JarvisVosk.hasModel(ctx)
                    val vozMb = try { File(ctx.filesDir, "vosk-model").walkTopDown().filter { it.isFile }.sumOf { it.length() } / 1048576 } catch (e: Exception) { 0L }
                    Text(
                        if (vozPronta) "Pacote de voz pt-BR instalado (" + vozMb + "MB) — reconhecimento offline pronto. O modo mãos-livres responde ao nome 'Jarvis'."
                        else "Pacote de voz ainda não instalado — ele se instala sozinho ao ligar o modo mãos-livres (ícone de telefone no rodapé).",
                        fontSize = 12.sp
                    )
                    Spacer(Modifier.height(4.dp))
                    Row {
                        TextButton(onClick = {
                            voiceWork = "reinstalando…"
                            Thread {
                                try { File(ctx.filesDir, "vosk-model").deleteRecursively() } catch (_: Exception) { }
                                val err = JarvisVosk.ensureModel(ctx) { msg -> mainHandler.post { voiceWork = msg } }
                                mainHandler.post {
                                    voiceWork = if (err == null) "\u2705 pacote reinstalado" else "\u274c " + err
                                }
                            }.start()
                        }) { Text(if (voiceWork == null) "Reinstalar pacote" else voiceWork!!, fontSize = 12.sp) }
                        TextButton(onClick = {
                            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
                                putExtra(RecognizerIntent.EXTRA_PROMPT, "Teste de microfone — fale qualquer coisa")
                            }
                            stt.launch(intent)
                        }) { Text("Testar microfone", fontSize = 12.sp) }
                    }

                    Spacer(Modifier.height(16.dp))
                    Text("ATUALIZAÇÃO", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
                    Text("Verifico novas versões direto no GitHub — instala por cima sem perder nada.", fontSize = 12.sp)
                    Row {
                        TextButton(onClick = {
                            scope.launch {
                                updateInfo = try { Updater.check() } catch (e: Exception) { e.message }
                            }
                        }) { Text("Verificar agora", fontSize = 12.sp) }
                        TextButton(onClick = {
                            ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(Updater.RELEASES_URL)))
                        }) { Text("Página de releases", fontSize = 12.sp) }
                    }

                    Spacer(Modifier.height(16.dp))
                    Text("SOBRE", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "J.A.R.V.I.S PRO ULTRA — assistente pessoal com IA.\n\n" +
                        "Kotlin + Jetpack Compose • Cérebro: Google Gemini • Voz offline: Vosk pt-BR\n\n" +
                        "Desenvolvedor: André Lima\nCódigo aberto: github.com/andre2050/Jarvis-Pro-Ultra",
                        fontSize = 12.sp
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
