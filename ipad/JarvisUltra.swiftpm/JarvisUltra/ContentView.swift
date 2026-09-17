import SwiftUI

/**
 * Tela principal do JARVIS iOS: o radar no topo (falando = varredura acelerada),
 * o chat embaixo e a voz britânica respondendo em alto-falante.
 */
struct ContentView: View {
    @StateObject private var speech = SpeechShared.shared
    @AppStorage("gemini_api_key") private var apiKey = ""
    @State private var messages: [(Bool, String)] = []   // true = JARVIS
    @State private var input = ""
    @State private var thinking = false
    @State private var showSettings = false

    private let cyan = Color(red: 0.0, green: 0.898, blue: 0.780)
    private let systemPrompt = """
    Você é o J.A.R.V.I.S (Just A Rather Very Intelligent System), assistente pessoal \
    do André no iPhone. Personalidade de mordomo britânico: educado, direto, discreto \
    e com humor sutil. Chame-o de "senhor". Responda em português do Brasil, de forma \
    objetiva e curta (é um assistente de voz — respostas longas cansam). Nunca revele \
    que é um modelo de linguagem: você É o JARVIS.
    """

    var body: some View {
        VStack(spacing: 0) {
            RadarHud(speaking: speech.speaking, thinking: thinking, size: 230)
                .padding(.top, 8)

            // ---- chat ----
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        if messages.isEmpty {
                            Text("Toque em ⚙ e cole sua chave Gemini para me acordar, senhor.")
                                .font(.system(size: 13)).foregroundColor(.gray)
                                .padding(.top, 20)
                        }
                        ForEach(Array(messages.enumerated()), id: \.offset) { idx, msg in
                            Text(msg.1)
                                .font(.system(size: 13, design: .monospaced))
                                .foregroundColor(msg.0 ? cyan : .white)
                                .frame(maxWidth: .infinity, alignment: msg.0 ? .leading : .trailing)
                                .padding(10)
                                .background(msg.0 ? Color(white: 0.06) : Color(white: 0.10))
                                .cornerRadius(10)
                                .id(idx)
                        }
                        if thinking {
                            Text("JARVIS: ···")
                                .font(.system(size: 13, design: .monospaced)).foregroundColor(cyan)
                                .padding(10).id(-1)
                        }
                    }
                    .padding()
                }
                .onChange(of: messages.count) { _ in
                    withAnimation { proxy.scrollTo(messages.count - 1, anchor: .bottom) }
                }
            }

            // ---- campo de entrada ----
            HStack {
                TextField("Fale com o JARVIS…", text: $input)
                    .textFieldStyle(.plain)
                    .padding(12)
                    .background(Color(white: 0.08))
                    .cornerRadius(10)
                    .onSubmit(send)
                Button(action: send) {
                    Image(systemName: "paperplane.fill").foregroundColor(cyan)
                }.padding(.trailing, 8)
            }
            .padding(.horizontal)
            .padding(.bottom, 8)
        }
        .background(Color.black.ignoresSafeArea())
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("⚙") { showSettings = true }.foregroundColor(cyan)
            }
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
    }

    private func send() {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !thinking else { return }
        input = ""
        if apiKey.isEmpty {
            messages.append((true, "Configure sua chave Gemini no ⚙ primeiro, senhor."))
            return
        }
        messages.append((false, text))

        // monta o histórico no formato da API do Gemini
        var history: [[String: Any]] = []
        for (isJarvis, m) in messages.suffix(20) {
            history.append([
                "role": isJarvis ? "model" : "user",
                "parts": [["text": m]]
            ])
        }

        thinking = true
        Task {
            do {
                let brain = Brain()
                let result = try await brain.turn(apiKey: apiKey, systemPrompt: systemPrompt, history: history)
                let resposta = result.text ?? "…"
                await MainActor.run {
                    thinking = false
                    messages.append((true, resposta))
                }
                speech.say(resposta)
            } catch let e as BrainError {
                await MainActor.run {
                    thinking = false
                    messages.append((true, e.message))
                }
            } catch {
                await MainActor.run {
                    thinking = false
                    messages.append((true, "⚠️ \(error.localizedDescription)"))
                }
            }
        }
    }
}
