package com.andre.jarvisultra

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.os.BatteryManager
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * WIDGET DO RADAR (v4.9.0): o holograma do JARVIS morando na tela inicial.
 * Anéis em teal, varredura, blips, hora e bateria — o mesmo visual do app,
 * redesenhado num Bitmap (widgets Compose não existem).
 *
 * Toque = chamar o JARVIS: abre o app já escutando o comando ("armado").
 */
class JarvisWidget : AppWidgetProvider() {

    override fun onUpdate(
        ctx: Context,
        manager: AppWidgetManager,
        ids: IntArray
    ) {
        val tocar = PendingIntent.getActivity(
            ctx, 4245,
            Intent(ctx, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                .putExtra("wake", true),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val views = RemoteViews(ctx.packageName, R.layout.widget_jarvis)
        val bitmap = desenharBusto(ctx)  // v4.9.3: única skin
        views.setImageViewBitmap(R.id.iv_radar, bitmap)
        views.setOnClickPendingIntent(R.id.iv_radar, tocar)
        for (id in ids) manager.updateAppWidget(id, views)
    }

    companion object {
        private const val TEAL = 0x00E5C7

        /** Desenha o holograma num Bitmap — serve pro widget e pra preview. */
        fun desenharRadar(ctx: Context, lado: Int = 512): Bitmap {
            val bmp = Bitmap.createBitmap(lado, lado, Bitmap.Config.ARGB_8888)
            val c = Canvas(bmp)
            val cx = lado / 2f
            val cy = lado / 2f
            val rMax = lado * 0.44f
            val fundo = Paint().apply {
                shader = RadialGradient(cx, cy, rMax * 1.2f,
                    Color.argb(255, 0x05, 0x14, 0x1E), Color.argb(255, 0x03, 0x08, 0x10),
                    Shader.TileMode.CLAMP)
            }
            c.drawCircle(cx, cy, rMax * 1.25f, fundo)

            val teal = Color.argb(255, 0x00, 0xE5, 0xC7)
            val tealFrac = Color.argb(70, 0x00, 0xE5, 0xC7)

            // anéis
            val anel = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                style = Paint.Style.STROKE
                color = tealFrac
                strokeWidth = lado * 0.006f
            }
            for (f in floatArrayOf(0.35f, 0.6f, 0.85f, 1f)) {
                c.drawCircle(cx, cy, rMax * f, anel)
            }

            // retículo
            val ret = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = tealFrac; strokeWidth = lado * 0.004f
            }
            c.drawLine(cx, cy - rMax, cx, cy + rMax, ret)
            c.drawLine(cx - rMax, cy, cx + rMax, cy, ret)

            // setor de varredura (fixo — widget redesenha a cada ciclo do sistema)
            val setor = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                isAntiAlias = true
                shader = android.graphics.SweepGradient(
                    cx, cy,
                    Color.argb(120, 0x00, 0xE5, 0xC7),
                    Color.argb(0, 0x00, 0xE5, 0xC7))
            }
            c.drawArc(cx - rMax, cy - rMax, cx + rMax, cy + rMax, 0f, 90f, true, setor)

            // agulha
            val agulha = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.argb(230, 0xFF, 0x44, 0x44); strokeWidth = lado * 0.008f
                strokeCap = Paint.Cap.ROUND
            }
            val ang = Math.toRadians(45.0)
            c.drawLine(cx, cy,
                (cx + rMax * Math.cos(ang)).toFloat(),
                (cy + rMax * Math.sin(ang)).toFloat(), agulha)

            // blips
            val blip = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = teal }
            val pontos = listOf(
                0.55f to 210f, 0.72f to 20f, 0.4f to 75f,
                0.66f to 140f, 0.3f to 330f, 0.8f to 285f, 0.5f to 165f
            )
            for ((d, a) in pontos) {
                val ra = Math.toRadians(a.toDouble())
                val px = (cx + rMax * d * Math.cos(ra)).toFloat()
                val py = (cy + rMax * d * Math.sin(ra)).toFloat()
                c.drawCircle(px, py, lado * 0.012f, blip)
            }

            // núcleo
            val nucleo = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.argb(200, 0x00, 0xE5, 0xC7)
            }
            c.drawCircle(cx, cy, lado * 0.035f, nucleo)

            // hora + bateria no rodapé
            val hora = SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(Date())
            val bateria = try {
                val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
                "${bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)}%"
            } catch (e: Exception) { "" }
            val txt = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.argb(230, 0x00, 0xE5, 0xC7)
                textSize = lado * 0.075f
                textAlign = Paint.Align.CENTER
                isFakeBoldText = true
            }
            val sub = Paint(txt).apply {
                textSize = lado * 0.05f; isFakeBoldText = false
                color = Color.argb(160, 0x8F, 0xB3, 0xC7)
            }
            c.drawText(hora, cx, cy + rMax * 0.98f, txt)
            c.drawText("J.A.R.V.I.S  ·  $bateria", cx, cy + rMax * 1.16f, sub)
            return bmp
        }

        /**
         * v4.9.4: o busto QUASE REAL no widget — a mesma arte do app
         * (res/drawable-nodpi/holo_busto.png) com hora e bateria no rodapé.
         */
        fun desenharBusto(ctx: Context, lado: Int = 512): Bitmap {
            val bmp = Bitmap.createBitmap(lado, lado, Bitmap.Config.ARGB_8888)
            val c = Canvas(bmp)
            val w = lado.toFloat(); val h = lado.toFloat()
            val cx = w / 2f

            // fundo
            c.drawRect(0f, 0f, w, h, Paint().apply {
                shader = RadialGradient(cx, h * 0.45f, w * 0.8f,
                    Color.argb(255, 0x06, 0x0C, 0x14), Color.argb(255, 0x02, 0x04, 0x08),
                    Shader.TileMode.CLAMP)
            })

            // a arte quase real
            try {
                val arte = BitmapFactory.decodeResource(ctx.resources, R.drawable.holo_busto)
                c.drawBitmap(arte, null, android.graphics.RectF(0f, 0f, w, h * 0.90f), Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
                arte.recycle()
            } catch (e: Exception) { /* fallback: fica só o fundo + texto */ }

            // faixa escura no rodapé pra legibilidade do relógio
            val fade = Paint().apply {
                shader = android.graphics.LinearGradient(0f, h * 0.78f, 0f, h,
                    Color.argb(0, 0, 0, 0), Color.argb(210, 2, 4, 8), Shader.TileMode.CLAMP)
            }
            c.drawRect(0f, h * 0.78f, w, h, fade)

            val hora = SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(Date())
            val bateria = try {
                val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
                "${bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)}%"
            } catch (e: Exception) { "" }
            val txt = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.argb(235, 0xE0, 0xF7, 0xFA)
                textSize = h * 0.052f; textAlign = Paint.Align.CENTER; isFakeBoldText = true
            }
            c.drawText("$hora  ·  J.A.R.V.I.S  ·  $bateria", cx, h * 0.97f, txt)
            return bmp
        }
    }
}
