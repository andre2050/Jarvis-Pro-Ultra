// swift-tools-version: 5.5
// JARVIS Ultra — edição Swift Playgrounds (iPad): compila e roda DIRETO no iPad,
// sem Mac e sem conta paga da Apple. Mesmos arquivos da versão Xcode.
import PackageDescription

let package = Package(
    name: "JarvisUltra",
    platforms: [.iOS("16.0")],
    products: [
        .iOSApplication(
            name: "JARVIS",
            targets: ["JarvisUltra"],
            bundleIdentifier: "com.andre.jarvisultra.ipad",
            teamIdentifier: nil,
            displayVersion: "4.7.1",
            appIcon: .placeholder(icon: .bolt),
            accentColor: .presetColor(.cyan),
            supportedDeviceFamilies: [.pad, .phone],
            supportedInterfaceOrientations: [.portrait, .landscapeLeft, .landscapeRight]
        )
    ],
    targets: [
        .executableTarget(
            name: "JarvisUltra",
            path: "JarvisUltra"
        )
    ]
)
