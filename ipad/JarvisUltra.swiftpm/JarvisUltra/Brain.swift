import Foundation

/**
 * Cérebro Gemini do JARVIS iOS — mesma cadeia de modelos do app Android
 * (v4.7.1): se um modelo foi aposentado (404), cai pro próximo.
 * v1 iOS: conversa pura (sem function calling — ferramentas chegam na v2).
 */
struct GeminiResult {
    let text: String?
    let model: String
}

final class Brain: ObservableObject {
    static let models = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]

    /// Uma rodada de conversa. history é o conteúdo no formato da API do Gemini.
    func turn(apiKey: String, systemPrompt: String, history: [[String: Any]]) async throws -> GeminiResult {
        var lastError: Error? = nil
        for m in Self.models {
            do {
                return try await callModel(m, apiKey: apiKey, systemPrompt: systemPrompt, history: history)
            } catch BrainError.retry {
                // 429/503: tenta o próximo modelo
                lastError = BrainError.overloaded
                continue
            } catch let e as BrainError {
                if e == .notFound { lastError = e; continue }
                throw e
            }
        }
        throw lastError ?? BrainError.noModel
    }

    private func callModel(_ model: String, apiKey: String, systemPrompt: String, history: [[String: Any]]) async throws -> GeminiResult {
        let payload: [String: Any] = [
            "system_instruction": ["parts": [["text": systemPrompt]]],
            "contents": history,
            "generationConfig": ["temperature": 0.7, "maxOutputTokens": 2048]
        ]        let url = URL(string: "https://generativelanguage.googleapis.com/v1beta/models/\(model):generateContent?key=\(apiKey)")!
        var req = URLRequest(url: url, timeoutInterval: 60)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        if code == 404 { throw BrainError.notFound }
        if code == 429 || code == 503 { throw BrainError.retry }
        guard (200..<300).contains(code) else {
            let msg = String(data: data, encoding: .utf8) ?? "sem detalhes"
            throw BrainError.api("HTTP \(code): \(msg.prefix(200))")
        }

        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        if let err = json["error"] as? [String: Any], let msg = err["message"] as? String {
            if msg.lowercased().contains("api key") { throw BrainError.api("⚠️ Chave do Gemini inválida, senhor. Confira em ⚙.") }
            throw BrainError.api(msg)
        }
        let candidates = json["candidates"] as? [[String: Any]] ?? []
        let content = candidates.first?["content"] as? [String: Any] ?? [:]
        let parts = content["parts"] as? [[String: Any]] ?? []
        let text = parts.compactMap { $0["text"] as? String }.joined(separator: "\n")
        return GeminiResult(text: text.isEmpty ? nil : text, model: model)
    }
}

enum BrainError: Error, Equatable {
    case notFound
    case retry
    case overloaded
    case noModel
    case api(String)

    static func == (lhs: BrainError, rhs: BrainError) -> Bool {
        switch (lhs, rhs) {
        case (.notFound, .notFound), (.retry, .retry), (.overloaded, .overloaded), (.noModel, .noModel): return true
        case (.api(let a), .api(let b)): return a == b
        default: return false
        }
    }

    var message: String {
        switch self {
        case .notFound: return "Nenhum modelo disponível no momento, senhor."
        case .retry, .overloaded: return "⚠️ Os servidores do Gemini estão sobrecarregados agora, senhor. Aguarde um minuto e mande de novo."
        case .noModel: return "Nenhum modelo respondeu, senhor."
        case .api(let m): return m
        }
    }
}
