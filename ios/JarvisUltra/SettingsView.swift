import SwiftUI

/**
 * ⚙ CONFIG do JARVIS iOS: chave do Gemini, teste de voz e atualização —
 * o mesmo painel do app Android, em SwiftUI.
 */
struct SettingsView: View {
    @AppStorage("gemini_api_key") private var apiKey = ""
    @State private var apiKeySaved = false
    @State private var updateMsg: String? = nil
    @State private var updateHasNew = false
    @State private var showUpdateButton = false
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL

    let cyan = Color(red: 0.0, green: 0.898, blue: 0.780)

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    // ---- CHAVE GEMINI ----
                    Text("CHAVE GEMINI")
                        .font(.system(size: 10, weight: .regular, design: .monospaced))
                        .foregroundColor(cyan).tracking(2)
                        .padding(.top, 16)
                    Text("Pegue grátis em aistudio.google.com. Fica só no seu aparelho.")
                        .font(.system(size: 12)).foregroundColor(.gray)
                        .padding(.top, 4)
                    SecureField("AIza...", text: $apiKey)
                        .textFieldStyle(.plain)
                        .padding(10)
                        .background(Color(white: 0.08))
                        .cornerRadius(8)
                        .padding(.top, 8)
                    Button("Salvar chave") { apiKeySaved = !apiKey.isEmpty }
                        .padding(.top, 8)
                    if !apiKey.isEmpty && apiKeySaved {
                        Text("\u{2705} Chave salva, senhor.").font(.system(size: 12)).padding(.top, 4)
                    }

                    // ---- VOZ ----
                    Text("VOZ")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(cyan).tracking(2)
                        .padding(.top, 24)
                    Text("Britânico (en-GB) · pitch 0.8 · velocidade de mordomo — a mesma das outras plataformas.")
                        .font(.system(size: 12)).foregroundColor(.gray)
                        .padding(.top, 4)
                    Button("Testar voz") { SpeechShared.shared.testVoice() }
                        .padding(.top, 8)

                    // ---- ATUALIZAÇÃO ----
                    Text("ATUALIZAÇÃO")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(cyan).tracking(2)
                        .padding(.top, 24)
                    Text("Verifico a versão nova direto no GitHub. No iOS a instalação é pela página de releases — o sistema não permite atualizar por dentro do app.", font: .system(size: 12))
                        .font(.system(size: 12)).foregroundColor(.gray)
                        .padding(.top, 4)
                    HStack {
                        Button("Verificar agora") {
                            updateMsg = "Verificando atualizações no GitHub, senhor…"
                            Task {
                                let r = await Updater.check()
                                updateMsg = r.msg
                                updateHasNew = r.hasUpdate
                            }
                        }
                        if updateHasNew {
                            Button("Abrir releases") { openURL(Updater.releasesURL) }
                                .foregroundColor(cyan)
                        }
                    }
                    .padding(.top, 8)
                    if let msg = updateMsg {
                        Text(msg).font(.system(size: 12)).foregroundColor(cyan).padding(.top, 4)
                    }

                    // ---- SOBRE ----
                    Text("SOBRE")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(cyan).tracking(2)
                        .padding(.top, 24)
                    Text("J.A.R.V.I.S PRO ULTRA — assistente pessoal com IA.\n\nSwiftUI • Cérebro: Google Gemini • Voz: en-GB nativa\n\nDesenvolvedor: André Lima\nCódigo aberto: github.com/andre2050/Jarvis-Pro-Ultra\n\nVersão \(AppInfo.version)")
                        .font(.system(size: 12))
                        .padding(.top, 4)
                        .padding(.bottom, 24)
                }
                .padding(.horizontal)
            }
            .background(Color.black.ignoresSafeArea())
            .navigationTitle("⚙ CONFIG")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Fechar") { dismiss() }
                }
            }
        }
    }
}

/// Instância única da voz compartilhada entre o app e a tela de config.
final class SpeechShared {
    static let shared = Speech()
}
