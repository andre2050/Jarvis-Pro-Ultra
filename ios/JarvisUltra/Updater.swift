import Foundation

/**
 * Verificador de atualização do JARVIS iOS: consulta a última release no
 * GitHub (a mesma do Android) e avisa quando há versão nova.
 *
 * ⚠️ No iOS a instalação silenciosa não existe — a App Store é a única loja.
 * Então aqui o fluxo é: avisar + abrir a página da release no Safari, onde o
 * APK/versão nova fica publicada. É o limite do sistema, senhor.
 */
struct UpdateResult {
    let msg: String
    let hasUpdate: Bool
}

enum Updater {
    static let releasesURL = URL(string: "https://github.com/andre2050/Jarvis-Pro-Ultra/releases")!
    private static let latestAPI = URL(string: "https://api.github.com/repos/andre2050/Jarvis-Pro-Ultra/releases/latest")!

    static func check() async -> UpdateResult {
        do {
            var req = URLRequest(url: latestAPI, timeoutInterval: 25)
            req.setValue("JarvisProUltra-iOS/\(AppInfo.version)", forHTTPHeaderField: "User-Agent")
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard (resp as? HTTPURLResponse)?.statusCode == 200 else {
                return UpdateResult(msg: "Não consegui consultar o servidor de atualização, senhor.", hasUpdate: false)
            }
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
            // v4.7.1-android → 4.7.1 (a tag mais recente é a do Android; a iOS
            // acompanha o mesmo número de versão)
            let tag = (json["tag_name"] as? String) ?? ""
            let versao = tag.dropFirst().prefix { $0 != "-" }
            let local = AppInfo.version
            if isNewer(String(versao), local) {
                return UpdateResult(msg: "Nova versão disponível: \(versao) (instalada: \(local)), senhor. Abra a página de releases.", hasUpdate: true)
            }
            return UpdateResult(msg: "Você está na versão mais recente, senhor. (\(local))", hasUpdate: false)
        } catch {
            return UpdateResult(msg: "Falha na verificação: \(error.localizedDescription)", hasUpdate: false)
        }
    }

    /// comparação de versões simples: 1.2.0 > 1.1.9
    private static func isNewer(_ remote: String, _ local: String) -> Bool {
        let r = remote.split(separator: ".").map { Int($0) ?? 0 }
        let l = local.split(separator: ".").map { Int($0) ?? 0 }
        for i in 0..<max(r.count, l.count) {
            let rv = i < r.count ? r[i] : 0
            let lv = i < l.count ? l[i] : 0
            if rv != lv { return rv > lv }
        }
        return false
    }
}

enum AppInfo {
    static let version = "4.7.1"
}
