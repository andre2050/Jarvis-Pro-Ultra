import SwiftUI
import UIKit

/**
 * O RADAR holográfico do JARVIS iOS — portado do Android (RadarHud.kt) e do
 * desktop v5.1.x: holograma circular teal com agulha vermelha varrendo, anéis
 * concêntricos, retículo, blips cintilantes e o núcleo pulsando com bateria,
 * hora e data. A varredura acelera quando ele pensa (1.1s), fala (1.7s) ou
 * fica parado (4s) — igual nas outras plataformas.
 */
struct RadarHud: View {
    var speaking: Bool = false
    var thinking: Bool = false
    var size: CGFloat = 240

    // paleta do radar (idêntica ao desktop v5.1.x / Android v4.7.x)
    private let teal = Color(red: 0.0, green: 0.898, blue: 0.780)       // 0x00E5C7
    private let tealDim = Color(red: 0.043, green: 0.431, blue: 0.388)  // 0x0B6E63
    private let needle = Color(red: 1.0, green: 0.353, blue: 0.302)     // 0xFF5A4D

    // blips fixos do radar (ângulo em radianos, distância 0.34–0.86)
    private let blips: [(Double, Double)] = [
        (0.7, 0.52), (2.1, 0.78), (3.4, 0.38), (4.2, 0.63), (5.1, 0.81), (0.2, 0.66), (2.9, 0.44)
    ]

    var body: some View {
        TimelineView(.animation) { timeline in
            Canvas { ctx, canvasSize in
                let t = timeline.date.timeIntervalSinceReferenceDate
                let w = canvasSize.width
                let h = canvasSize.height
                let cx = w / 2
                let cy = h / 2
                let r = min(w, h) * 0.42

                // respiração (ciclo de 2.6s) e varredura (acelera com a energia)
                let breathe = (sin(2 * .pi * t / 2.6) + 1) / 2
                let dur = thinking ? 1.1 : (speaking ? 1.7 : 4.0)
                let sweep = (t.truncatingRemainder(dividingBy: dur)) / dur * 360
                let slowSpin = t.truncatingRemainder(dividingBy: 24) / 24 * 360

                // ---- halo de fundo ----
                ctx.fill(
                    Path(ellipseIn: CGRect(x: cx - r * 1.12, y: cy - r * 1.12, width: r * 2.24, height: r * 2.24)),
                    with: .radialGradient(
                        Gradient(colors: [teal.opacity(0.14 + 0.10 * breathe), .clear]),
                        center: CGPoint(x: cx, y: cy), startRadius: 0, endRadius: r * 1.12))

                // ---- retículo ----
                var reticle = Path()
                reticle.move(to: CGPoint(x: cx - r * 1.05, y: cy))
                reticle.addLine(to: CGPoint(x: cx + r * 1.05, y: cy))
                reticle.move(to: CGPoint(x: cx, y: cy - r * 1.05))
                reticle.addLine(to: CGPoint(x: cx, y: cy + r * 1.05))
                ctx.stroke(reticle, with: .color(tealDim.opacity(0.45)), lineWidth: 1)

                // ---- anéis concêntricos ----
                for f in [1.0, 0.74, 0.47, 0.24] {
                    let ring = Path(ellipseIn: CGRect(x: cx - r * f, y: cy - r * f, width: r * 2 * f, height: r * 2 * f))
                    ctx.stroke(ring, with: .color(teal.opacity(f == 1.0 ? 0.9 : 0.42)), lineWidth: f == 1.0 ? 2 : 1)
                }

                // ---- trilha da varredura (12 fatias com alpha decrescente) ----
                for i in 0..<12 {
                    let start = sweep - 48 - Double(i) * 4
                    var trail = Path()
                    trail.move(to: CGPoint(x: cx, y: cy))
                    trail.addArc(center: CGPoint(x: cx, y: cy), radius: r,
                                 startAngle: .degrees(start), endAngle: .degrees(start + 5),
                                 clockwise: false)
                    trail.closeSubpath()
                    ctx.fill(trail, with: .color(teal.opacity(0.20 * (1.0 - Double(i) / 12))))
                }

                // ---- blips cintilando (orbitam devagar) ----
                for (idx, blip) in blips.enumerated() {
                    let flick = 0.35 + 0.65 * (sin(2 * .pi * t / 1.3 + Double(idx) * 1.9) + 1) / 2
                    if flick > 0.38 {
                        let a = blip.0 + slowSpin * .pi / 180 * 0.35
                        let bx = cx + r * blip.1 * cos(a)
                        let by = cy + r * blip.1 * sin(a)
                        ctx.fill(Path(ellipseIn: CGRect(x: bx - 2.2, y: by - 2.2, width: 4.4, height: 4.4)),
                                 with: .color(needle.opacity(0.3 + 0.7 * flick)))
                    }
                }

                // ---- agulha vermelha ----
                let na = sweep * .pi / 180
                var line = Path()
                line.move(to: CGPoint(x: cx, y: cy))
                line.addLine(to: CGPoint(x: cx + r * cos(na), y: cy + r * sin(na)))
                ctx.stroke(line, with: .color(needle), lineWidth: 2)

                // ---- rótulos técnicos ao redor ----
                let labels: [(Double, String)] = [(-135, "ULTRA"), (-45, "RADAR"), (135, "GEMINI"), (45, "VOZ")]
                for (deg, label) in labels {
                    let a = deg * .pi / 180
                    ctx.draw(
                        Text(label).font(.system(size: r * 0.072, weight: .regular, design: .monospaced))
                            .foregroundColor(teal.opacity(0.8)).tracking(1.4),
                        at: CGPoint(x: cx + r * 1.13 * cos(a), y: cy + r * 1.13 * sin(a)))
                }

                // ---- núcleo pulsante ----
                let energia = (speaking || thinking) ? 1.6 : 1.0
                let core = r * 0.15 * (1 + 0.22 * breathe * energia)
                ctx.fill(
                    Path(ellipseIn: CGRect(x: cx - core * 2.4, y: cy - core * 2.4, width: core * 4.8, height: core * 4.8)),
                    with: .radialGradient(
                        Gradient(colors: [teal.opacity(0.75), tealDim.opacity(0.18)]),
                        center: CGPoint(x: cx, y: cy), startRadius: 0, endRadius: core * 2.4))
                ctx.fill(Path(ellipseIn: CGRect(x: cx - core, y: cy - core, width: core * 2, height: core * 2)),
                        with: .color(teal))

                // ---- leituras do aparelho sob o núcleo ----
                let fmtHora = DateFormatter()
                fmtHora.dateFormat = "HH:mm"
                let fmtData = DateFormatter()
                fmtData.dateFormat = "d 'de' MMM"
                fmtData.locale = Locale(identifier: "pt_BR")
                UIDevice.current.isBatteryMonitoringEnabled = true
                let bat = Int((UIDevice.current.batteryLevel * 100).rounded())
                ctx.draw(
                    Text("\(fmtHora.string(from: Date())) · \(fmtData.string(from: Date()).uppercased())")
                        .font(.system(size: r * 0.082, design: .monospaced)).foregroundColor(teal.opacity(0.92)),
                    at: CGPoint(x: cx, y: cy + r * 0.55))
                ctx.draw(
                    Text(thinking ? "PROCESSANDO ···" : "BAT \(bat)%")
                        .font(.system(size: r * 0.072, design: .monospaced)).foregroundColor(tealDim),
                    at: CGPoint(x: cx, y: cy + r * 0.68))
            }
        }
        .frame(width: size, height: size)
    }
}
