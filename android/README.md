# JARVIS PRO ULTRA — Android (Kotlin)

App Android nativo do assistente JARVIS PRO ULTRA. Mesma alma do projeto desktop:
Gemini + registry de tools com function calling real — agora com rosto holográfico
animado em Jetpack Compose e voz nativa do Android.

## Funcionalidades (v1.0.0)

- **Rosto holográfico animado** — olhos que piscam em intervalos naturais, pupilas que vagam,
  boca sincronizada com a fala e anel reator pulsante (Compose Canvas)
- **Voz bidirecional** — fala com TTS nativo pt-BR e ouve você pelo reconhecimento de fala do Google (botão do microfone)
- **Cérebro Gemini com tools reais** — mesmo protocolo do desktop: o modelo chama `calcular`,
  `hora_e_data`, `status_dispositivo` e `piada` quando precisa, em loop de function calling
- **Calculadora segura** — parser de expressões próprio, sem `eval` (aceita + - * / % e parênteses)
- **Verificador de atualização** — lê o MESMO `update.json` assinado das Releases do GitHub
- **Chave do Gemini no dispositivo** — fica em SharedPreferences privados, nunca no código nem no repo

## Compilar o APK

Requisitos: JDK 17, Android SDK (platform 34, build-tools 34.0.0), Gradle 8.7+.

```bash
# aponte o SDK (ou use o Android Studio, que faz isso sozinho)
echo "sdk.dir=/caminho/do/Android/Sdk" > local.properties

# APK de teste (debug)
gradle :app:assembleDebug
# → app/build/outputs/apk/debug/app-debug.apk

# APK de produção (release assinado)
export JARVIS_KEYSTORE=/caminho/jarvis-release.jks
export JARVIS_KEYSTORE_PASS='suaSenha'
export JARVIS_KEY_ALIAS=jarvis
export JARVIS_KEY_PASS='suaSenha'
gradle :app:assembleRelease
# → app/build/outputs/apk/release/app-release.apk
```

> ⚠️ **Assinatura**: o keystore `jarvis-release.jks` fica FORA do repo
> (guarde-o junto com `keys/ed25519_private.pem`). Atualizações do app só instalam
> por cima se assinadas com a MESMA chave.

## Instalar no celular

1. Baixe o APK e abra (o Android pede permissão para instalar apps desconhecidos)
2. Abra o app e cole sua chave do Google AI Studio nas configurações (a chave fica só no aparelho)
3. Fale ou digite uma ordem

## Estrutura

```
app/src/main/java/com/andre/jarvisultra/
├── MainActivity.kt      — entry point + tema holográfico
├── JarvisScreen.kt      — UI: chat, microfone, configurações, updater
├── HologramFace.kt      — rosto animado (Canvas Compose)
├── JarvisVoice.kt       — TTS pt-BR com listener de boca animada
├── JarvisBrain.kt       — persona + loop de function calling
├── GeminiClient.kt      — API Gemini (OkHttp, coroutines)
├── JarvisTools.kt       — registry de tools + parser matemático
├── SettingsStore.kt     — configurações locais (SharedPreferences)
└── Updater.kt           — checagem contra update.json das Releases
```

## Próximas versões (roadmap)

- [ ] Notificações proativas e alarmes
- [ ] Mais tools: abrir apps, timer, flashlight, localização
- [ ] Download e instalação de APK in-app (com verificação Ed25519 do manifesto)
- [ ] Widget do holograma na tela inicial
