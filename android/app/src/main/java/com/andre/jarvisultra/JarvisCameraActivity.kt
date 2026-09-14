package com.andre.jarvisultra

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.ViewGroup
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cameraswitch
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat

/**
 * Câmera nativa do JARVIS (v4.6.0 — Ambos os Olhos).
 * Fullscreen com preview CameraX, botão de alternar frontal/traseira e obturador.
 * A foto volta pra JarvisScreen pelo result extra "foto_path" e segue
 * direto pro Gemini (multimodal) — o mesmo pipeline da visão computacional.
 */
class JarvisCameraActivity : ComponentActivity() {

    companion object {
        const val EXTRA_FACING = "facing"
        const val EXTRA_PATH = "foto_path"
    }

    private var imageCapture: ImageCapture? = null
    private var provider: ProcessCameraProvider? = null
    private val executor by lazy { ContextCompat.getMainExecutor(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            setResult(RESULT_CANCELED)
            finish()
            return
        }

        val initialFacing = intent.getIntExtra(EXTRA_FACING, CameraSelector.LENS_FACING_BACK)

        setContent {
            var facing by remember { mutableStateOf(initialFacing) }
            var providerReady by remember { mutableStateOf(false) }
            var capturing by remember { mutableStateOf(false) }
            val previewView = remember { PreviewView(this@JarvisCameraActivity).apply { layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT) } }

            // provider async — quando pronto, liga a câmera
            LaunchedEffect(Unit) {
                val future = ProcessCameraProvider.getInstance(this@JarvisCameraActivity)
                future.addListener({
                    provider = future.get()
                    providerReady = true
                }, executor)
            }

            // (re)binda quando o provider fica pronto ou quando o senhor alterna a câmera
            LaunchedEffect(providerReady, facing) {
                if (providerReady) bindCamera(previewView, facing)
            }

            Box(Modifier.fillMaxSize().background(Color(0xFF040B14))) {
                AndroidView(factory = { previewView }, modifier = Modifier.fillMaxSize())

                // ---- HUD topo: fechar + etiqueta da câmera ----
                Column(Modifier.fillMaxWidth().statusBarsPadding()) {
                    Row(Modifier.fillMaxWidth().padding(start = 4.dp, end = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { setResult(RESULT_CANCELED); finish() }) {
                            Icon(Icons.Default.Close, contentDescription = "Fechar câmera", tint = Cyan)
                        }
                        Text(
                            if (facing == CameraSelector.LENS_FACING_FRONT) "JARVIS · CÂMERA FRONTAL" else "JARVIS · CÂMERA TRASEIRA",
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Cyan.copy(alpha = 0.85f),
                            letterSpacing = 2.sp
                        )
                    }
                    Spacer(Modifier.height(2.dp))
                    Box(Modifier.fillMaxWidth().height(1.dp).background(HoloLine))
                }

                // ---- controles de rodapé: alternar + obturador ----
                Row(
                    Modifier.fillMaxWidth().align(Alignment.BottomCenter).padding(bottom = 34.dp).navigationBarsPadding(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // alternar frontal/traseira
                    Box(
                        Modifier.size(54.dp).background(Cyan.copy(alpha = 0.12f), CircleShape).border(1.dp, Cyan.copy(alpha = 0.55f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        IconButton(onClick = {
                            facing = if (facing == CameraSelector.LENS_FACING_FRONT) CameraSelector.LENS_FACING_BACK else CameraSelector.LENS_FACING_FRONT
                        }) {
                            Icon(Icons.Default.Cameraswitch, contentDescription = "Alternar câmera", tint = Cyan)
                        }
                    }

                    Spacer(Modifier.size(38.dp))

                    // obturador
                    IconButton(onClick = { if (!capturing) { capturing = true; takePhoto() } }, modifier = Modifier.size(76.dp)) {
                        Box(
                            Modifier.size(64.dp).background(Color.White, CircleShape).border(4.dp, Cyan, CircleShape)
                        )
                    }
                }
            }
        }
    }

    private fun bindCamera(view: PreviewView, facing: Int) {
        val p = provider ?: return
        p.unbindAll()
        try {
            val preview = Preview.Builder().build().also { it.setSurfaceProvider(view.surfaceProvider) }
            val capture = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .build()
            val selector = CameraSelector.Builder().requireLensFacing(facing).build()
            p.bindToLifecycle(this, selector, preview, capture)
            imageCapture = capture
        } catch (e: Exception) {
            setResult(RESULT_CANCELED, Intent().putExtra("erro", e.message))
            finish()
        }
    }

    private fun takePhoto() {
        val capture = imageCapture ?: run { setResult(RESULT_CANCELED); finish(); return }
        val dir = java.io.File(cacheDir, "visao").apply { mkdirs() }
        val foto = java.io.File(dir, "jarvis_olho_${System.currentTimeMillis()}.jpg")
        val opts = ImageCapture.OutputFileOptions.Builder(foto).build()
        capture.takePicture(opts, executor, object : ImageCapture.OnImageSavedCallback {
            override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                setResult(RESULT_OK, Intent().putExtra(EXTRA_PATH, foto.absolutePath))
                finish()
            }
            override fun onError(exception: ImageCaptureException) {
                setResult(RESULT_CANCELED)
                finish()
            }
        })
    }

    override fun onDestroy() {
        super.onDestroy()
        provider?.unbindAll()
    }
}
