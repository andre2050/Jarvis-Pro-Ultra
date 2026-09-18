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
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.PhotoCamera
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
    var updateApk by remember { mutableStateOf<Pair<String, String>?>(null) }
    var updateMsg by remember { mutableStateOf<String?>(null) }
    var testResult by remember { mutableStateOf<String?>(null) }
    var voiceWork by remember { mutableStateOf<String?>(null) }
    var suggestion by remember { mutableStateOf<JarvisMemory.Suggestion?>(null) }
    var handsFree by remember { mutableStateOf("off") }
    var tema by remember { mutableStateOf(SettingsStore.getTheme(ctx)) }
    var voskSession by remember { mutableStateOf<JarvisVosk.Session?>(null) }
    // --- VISÃO COMPUTACIONAL v4.5.0 ---
    var pendingFacing by remember { mutableStateOf(androidx.camera.core.CameraSelector.LENS_FACING_BACK) }
    var visaoPergunta by remember { mutableStateOf<String?>(null) }
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
                android.Manifest.permission.ACCESS_FINE_LOCATION,
                android.Manifest.permission.CAMERA
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

    // --- VISÃO: análise da foto capturada (multimodal no Gemini) ---
    fun analisarFoto(uri: Uri) {
        if (isThinking) return
        if (!apiKeySaved) {
            messages = messages + ChatMessage("model", "Ainda não tenho a chave do Gemini, senhor — sem ela eu sou cego. Toque na engrenagem e cole a chave.")
            return
        }
        val pergunta = (visaoPergunta ?: "O que você está vendo, JARVIS? Descreva de forma curta e útil.").trim()
        messages = messages + ChatMessage("user", "📷 " + pergunta) + ChatMessage("model", "…")
        isThinking = true
        scope.launch {
            val key = SettingsStore.getApiKey(ctx)
            val enc = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                JarvisVisao.codificarParaGemini(ctx, uri)
            }
            val result = if (enc == null) {
                JarvisBrain.TurnResult("Não consegui processar a foto, senhor — tente de novo, de preferência com mais luz.", history, emptyList())
            } else {
                try {
                    JarvisBrain.process(ctx, key, history, pergunta, imageB64 = enc.first, imageMime = enc.second)
                } catch (e: Exception) {
                    JarvisBrain.TurnResult(e.message ?: "erro inesperado", history, emptyList())
                }
            }
            isThinking = false
            val reply = result.reply.ifBlank { "Às ordens, senhor." }
            messages = messages.dropLast(1) + ChatMessage("model", reply)
            if (!reply.startsWith("⚠️")) voice.speak(reply)
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    val cameraActivity = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
        if (res.resultCode == Activity.RESULT_OK) {
            res.data?.getStringExtra(JarvisCameraActivity.EXTRA_PATH)?.let { path ->
                analisarFoto(Uri.fromFile(java.io.File(path)))
            }
        }
    }

    val camPerm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            cameraActivity.launch(
                Intent(ctx, JarvisCameraActivity::class.java).putExtra(JarvisCameraActivity.EXTRA_FACING, pendingFacing)
            )
        } else {
            messages = messages + ChatMessage("model", "Preciso da permissão da câmera para enxergar, senhor — toque no ícone de foto de novo quando liberar.")
        }
    }

    /** Abre a câmera NATIVA do JARVIS. cameraChoice: "frontal" | "traseira" | null (padrão traseira) */
    fun abrirCamera(pergunta: String?, cameraChoice: String? = null) {
        visaoPergunta = pergunta
        pendingFacing = if (cameraChoice == "frontal")
            androidx.camera.core.CameraSelector.LENS_FACING_FRONT
        else androidx.camera.core.CameraSelector.LENS_FACING_BACK
        if (ContextCompat.checkSelfPermission(ctx, android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            cameraActivity.launch(
                Intent(ctx, JarvisCameraActivity::class.java).putExtra(JarvisCameraActivity.EXTRA_FACING, pendingFacing)
            )
        } else camPerm.launch(android.Manifest.permission.CAMERA)
    }

    // quando o GEMINI chamar a tool ver_camera, a câmera abre por aqui
    DisposableEffect(Unit) {
        JarvisVisao.onCaptureRequest = { pergunta, camera -> mainHandler.post { abrirCamera(pergunta, camera) } }
        onDispose { JarvisVisao.onCaptureRequest = null }
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
            Brush.verticalGradient(listOf(Color(0xFF071522), Color(0xFF040B14), Color(0xFF01050A)))
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
        Row(
            modifier = Modifier.fillMaxWidth().padding(start = 12.dp, end = 12.dp, top = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "JARVIS OS · v" + JarvisBrain.APP_VERSION,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                color = Cyan.copy(alpha = 0.75f),
                letterSpacing = 1.5.sp
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("SENHOR", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = CyanDim, letterSpacing = 1.sp)
                Spacer(Modifier.width(6.dp))
                Box(
                    Modifier
                        .size(22.dp)
                        .background(Cyan.copy(alpha = 0.14f), CircleShape)
                        .border(1.dp, Cyan.copy(alpha = 0.6f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text("A", fontSize = 11.sp, color = Cyan, fontFamily = FontFamily.Monospace)
                }
            }
        }
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    StatChip(label = "MEM", value = memPct(ctx) + "%")
                    Spacer(Modifier.height(8.dp))
                    StatChip(label = "VOZ", value = if (handsFree == "on") "ON" else "OFF")
                }
                if (tema == "radar") {
                    RadarHud(
                        modifier = Modifier
                            .padding(top = 8.dp, bottom = 4.dp, start = 6.dp, end = 6.dp)
                            .size(190.dp),
                        ctx = ctx,
                        isSpeaking = isSpeaking,
                        isThinking = isThinking,
                        isListening = (handsFree == "on")
                    )
                } else {
                    ArcReactorHud(
                        modifier = Modifier
                            .padding(top = 8.dp, bottom = 4.dp, start = 6.dp, end = 6.dp)
                            .size(190.dp),
                        ctx = ctx,
                        isSpeaking = isSpeaking,
                        isThinking = isThinking,
                        isListening = (handsFree == "on")
                    )
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    StatChip(label = "NET", value = netStatus(ctx))
                    Spacer(Modifier.height(8.dp))
                    StatChip(label = "GPS", value = if (hasLocationPermission(ctx)) "ON" else "OFF")
                }
            }
            Row(Modifier.align(Alignment.TopEnd).padding(10.dp)) {
                IconButton(onClick = {
                    updateInfo = "Verificando atualizações no GitHub, senhor…"
                    scope.launch {
                        updateInfo = try { Updater.check() } catch (e: Exception) { e.message ?: "erro de conexão ao verificar atualização" }
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
            modifier = Modifier.align(Alignment.CenterHorizontally).padding(top = 2.dp, bottom = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(Modifier.width(28.dp).height(1.dp).background(HoloLine))
            Text(
                "  J . A . R . V . I . S   P R O   U L T R A  ",
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
                color = CyanDim,
                letterSpacing = 1.sp
            )
            Box(Modifier.width(28.dp).height(1.dp).background(HoloLine))
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
                        color = if (isUser) Cyan.copy(alpha = 0.12f) else Color(0xF2071522),
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
            color = Color(0xD90A1826),
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
            // ---- chips de comandos rápidos (v4.7.3) ----
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 10.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                listOf(
                    "⏰ Alarme 7h" to "Define um alarme às 7 da manhã",
                    "☁️ Clima" to "Como está o clima agora?",
                    "🛰 Modo mesa" to "Abra o modo mesa",
                    "💡 Lanterna" to "Liga a lanterna",
                    "📱 YouTube" to "Abre o YouTube",
                    "📞 Ligar" to "Pelo que eu posso te ligar, JARVIS? Use a tool ligar_para."
                ).forEach { (rotulo, cmd) ->
                    Surface(
                        onClick = { if (!isThinking) send(cmd) },
                        color = Color(0x1200E5C7),
                        contentColor = Cyan,
                        border = BorderStroke(1.dp, HoloLine),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Text(rotulo, fontSize = 12.sp,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp))
                    }
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

                IconButton(onClick = { abrirCamera(null) }) {
                    Icon(Icons.Default.PhotoCamera, contentDescription = "Visão — abrir câmera", tint = Cyan)
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
                    placeholder = { Text("Mande uma ordem, senhor…", fontSize = 14.sp, color = Color(0xFF5A7A8A)) },
                    singleLine = true,
                    shape = RoundedCornerShape(18.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Cyan,
                        unfocusedBorderColor = HoloLine,
                        focusedTextColor = Color(0xFFE2F3FA),
                        unfocusedTextColor = Color(0xFFE2F3FA),
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
                    Text("TEMA DO HOLOGRAMA", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
                    Text("O radar holográfico teal da edição desktop v5.1 — ou o Reator de Arco vermelho clássico. Troca na hora, sem reiniciar.", fontSize = 12.sp)
                    Spacer(Modifier.height(4.dp))
                    Row {
                        TextButton(onClick = {
                            SettingsStore.setTheme(ctx, "radar"); tema = "radar"
                        }) { Text(if (tema == "radar") "\u25cf Radar (ativo)" else "Radar", fontSize = 12.sp, color = if (tema == "radar") Cyan else Color.Unspecified) }
                        TextButton(onClick = {
                            SettingsStore.setTheme(ctx, "arc"); tema = "arc"
                        }) { Text(if (tema == "arc") "\u25cf Reator de Arco (ativo)" else "Reator de Arco", fontSize = 12.sp, color = if (tema == "arc") Cyan else Color.Unspecified) }
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
                    Text("Verifico a versão nova direto no GitHub, baixo o APK e abro o instalador — você só confirma na tela. A partir da v4.7.1 toda atualização instala por cima sem perder nada.", fontSize = 12.sp)
                    Row {
                        TextButton(onClick = {
                            updateMsg = "Verificando atualizações no GitHub, senhor…"
                            scope.launch {
                                try {
                                    val r = Updater.checar()
                                    updateMsg = r.msg
                                    updateApk = if (r.apkUrl != null) Pair(r.apkUrl, r.apkName ?: "atualizacao.apk") else null
                                } catch (e: Exception) {
                                    updateMsg = e.message ?: "erro de conexão ao verificar atualização"
                                }
                            }
                        }) { Text("Verificar agora", fontSize = 12.sp) }
                        TextButton(onClick = {
                            ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(Updater.RELEASES_URL)))
                        }) { Text("Página de releases", fontSize = 12.sp) }
                    }
                    if (updateApk != null) {
                        TextButton(onClick = {
                            val (url, _) = updateApk!!
                            updateMsg = "Iniciando download, senhor…"
                            updateApk = null
                            scope.launch {
                                try {
                                    val apk = Updater.baixar(ctx, url) { prog -> updateMsg = prog }
                                    updateMsg = "Download concluído — abrindo o instalador. Confirme na tela."
                                    Updater.instalar(ctx, apk)
                                } catch (e: Exception) {
                                    updateMsg = "Falha no download: ${e.message ?: "sem detalhes"}"
                                }
                            }
                        }) { Text("Baixar e instalar agora", fontSize = 12.sp, color = Cyan) }
                    }
                    updateMsg?.let { ui ->
                        Text(ui, fontSize = 12.sp, color = Cyan)
                    }

                    Spacer(Modifier.height(16.dp))
                    Text("CATÁLOGO DE COMANDOS", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Fale no 🎙 (ou no ícone de telefone pra mãos-livres) ou digite — eu executo:\n\n" +
                        "📞 Ligar pra Edna · Mandar WhatsApp pra Edna dizendo 'cheguei'\n" +
                        "⏰ Alarme às 7h · Timer de 10 minutos\n" +
                        "📅 Lembrar dentista amanhã às 15h (abre na agenda)\n" +
                        "✉️ Enviar email para fulano@x.com\n" +
                        "📱 Abrir YouTube · Pesquisar resultado do jogo\n" +
                        "💡 Liga a lanterna · Como tá o clima? · Onde eu estou?\n" +
                        "🛰 Abrir modo mesa · O que você lembra de mim?\n\n" +
                        "Tudo por permissões oficiais do Android, sem root.",
                        fontSize = 12.sp
                    )

                    Spacer(Modifier.height(16.dp))
                    Text("MODO MESA/CARRO", fontSize = 10.sp, fontFamily = FontFamily.Monospace, color = Cyan, letterSpacing = 2.sp)
                    Spacer(Modifier.height(6.dp))
                    Text("Tela cheia sempre ligada: radar grande, relógio, clima ao vivo e bateria — o celular vira um painel do Homem de Ferro. Toque na tela pra sair.", fontSize = 12.sp)
                    TextButton(onClick = {
                        ctx.startActivity(Intent(ctx, DeskModeActivity::class.java))
                    }) { Text("Abrir modo mesa", fontSize = 12.sp, color = Cyan) }

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
