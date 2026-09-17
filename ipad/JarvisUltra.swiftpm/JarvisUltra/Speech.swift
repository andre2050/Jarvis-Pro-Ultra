import AVFoundation
import SwiftUI

/**
 * A voz do mordomo: motor nativo do iOS (AVSpeechSynthesizer) com a MESMA
 * configuração das outras plataformas — britânico (en-GB), pitch 0.8,
 * velocidade de mordomo. Zero dependências.
 */
final class Speech: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    @Published var speaking = false
    @Published var usingNative = true

    private let synth = AVSpeechSynthesizer()

    override init() {
        super.init()
        synth.delegate = self
    }

    /// Fala o texto com a voz padrão do JARVIS.
    func say(_ text: String) {
        stop()
        let u = AVSpeechUtterance(string: text)
        u.voice = AVSpeechSynthesisVoice(language: "en-GB")
        u.pitchMultiplier = 0.8
        u.rate = AVSpeechUtteranceMaximumSpeechRate * 0.42   // velocidade de mordomo (~0.85 da normal)
        u.volume = 1.0
        speaking = true
        synth.speak(u)
    }

    /// Frase de teste padrão do JARVIS (a mesma do desktop e do Android).
    func testVoice() {
        say("Good evening. All systems are online and operating at full capacity.")
    }

    func stop() {
        synth.stopSpeaking(at: .immediate)
        speaking = false
    }

    // MARK: - AVSpeechSynthesizerDelegate

    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        DispatchQueue.main.async { self.speaking = false }
    }

    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        DispatchQueue.main.async { self.speaking = false }
    }
}
