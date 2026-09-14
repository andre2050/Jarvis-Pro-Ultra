<div align="center">

<img src="https://media.base44.com/images/public/6aa358a021b0a981485d8eb1/86212ad71_generated_image.png" alt="JARVIS PRO ULTRA — interface JARVIS OS" width="820">

# J.A.R.V.I.S PRO ULTRA

**O assistente pessoal com IA que fala português, escuta offline e controla seu aparelho inteiro.**

`Android 4.5.0 · Olhos de Ferro` · `Desktop 5.0.2 · Ollama offline` · `Core Python`

[![Última release](https://img.shields.io/github/v/release/andre2050/Jarvis-Pro-Ultra?style=flat-square&color=2FD8FF&label=release)](https://github.com/andre2050/Jarvis-Pro-Ultra/releases/latest)
[![Releases](https://img.shields.io/github/downloads/andre2050/Jarvis-Pro-Ultra/total?style=flat-square&label=downloads)](https://github.com/andre2050/Jarvis-Pro-Ultra/releases)
[![Plataforma](https://img.shields.io/badge/plataforma-Android%20%7C%20Windows%20%7C%20macOS%20%7C%20Linux-2FD8FF?style=flat-square)](https://github.com/andre2050/Jarvis-Pro-Ultra)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-CC%20BY--NC%204.0-163247?style=flat-square)](https://creativecommons.org/licenses/by-nc/4.0/)

</div>

---

## 🆕 v4.5.0 — Olhos de Ferro (Visão Computacional)

O JARVIS agora **enxerga**:

- 👁️ **Botão de câmera** 📷 na barra de comando — fotografe e ele analisa na hora
- 🗣️ **Por voz** — "Jarvis, o que você vê?", "leia o que está escrito aqui", "o que é isso?" — ele chama a tool `ver_camera` e abre a câmera sozinho
- 🧠 **Multimodal real** — a foto é reduzida (≤1024px), comprimida em JPEG e enviada ao Gemini como `inline_data`: descrição de cenas, transcrição de textos (etiquetas, contas, papéis), identificação de objetos, tudo respondido em português e falado em voz alta
- 🔒 Foto temporária em cache via FileProvider — nada fica gravado na galeria

## v4.4.0 — JARVIS OS

A interface virou o sistema operacional do filme. A tela principal agora é um cockpit de dados vivos:

- 🔷 **Paleta azul-ciano estilo Stark Industries** — todo o app segue o tom clássico do JARVIS
- 🔺 **Núcleo triangular** — o centro do reator é o glifo triangular icônico, com um triângulo interno girando lentamente e um ponto de luz pulsante no meio
- 📊 **Painéis de dados REAIS** flanqueando o reator — nada decorativo:
  - `MEM` — uso real de RAM do aparelho (via `ActivityManager`)
  - `NET` — Wi-Fi / dados / offline (via `ConnectivityManager`)
  - `GPS` — status da permissão de localização
  - `VOZ` — mãos-livres ligado ou desligado
- 🏷️ **Cabeçalho `JARVIS OS · vX`** com avatar `SENHOR`
- ⚡ **Bateria e hora ao vivo** logo abaixo do glifo, atualizando a cada segundo
- ⚙️ **Painel de Configurações** (desde a v4.2.0): 🎙️ **Microfone** (status do pacote de voz, reinstalar, testar), **Atualização** (verificar na hora ou abrir releases), **Sobre** e chave do Gemini
- 🚀 **Performance**: renderização do reator sem alocação por frame — Paints reciclados, 60fps limpo (v4.3.1)

## 📥 Instalação (Android)

Baixe o APK direto da [última release](https://github.com/andre2050/Jarvis-Pro-Ultra/releases/latest) e instale por cima — a assinatura é a mesma em todas as versões, sem precisar desinstalar nada.

> Requer Android 8.0+. Na primeira abertura o app pede as permissões (contatos, SMS, notificações, localização, microfone) — cada função explica o porquê.

## 🧠 O que ele faz

| Módulo | Capacidades |
|---|---|
| 🗣️ **Voz neural** | Reconhecimento **100% offline** (Vosk pt-BR, embutido no APK), síntese de voz nativa e modo mãos-livres que responde à palavra "Jarvis" |
| 🤖 **Cérebro Gemini** | Conversa natural com histórico, contexto do aparelho injetado a cada turno (hora, bateria, carregando, volume, rede, localização) — ele *sabe* sem você contar |
| 📞 **Controle total** | Ligações (com busca em contatos), WhatsApp com texto pré-preenchido, envio/leitura de SMS, leitura de notificações (WhatsApp e SMS via `NotificationListenerService`), alarmes, lanterna, abrir apps, timer, busca na web |
| 👁️ **Visão** | Câmera + multimodal: descreve cenas, lê textos físicos (etiquetas, contas), identifica objetos — por botão ou por voz |
| 🌍 **Percepção** | Clima em tempo real via GPS (Open-Meteo, sem API key), "onde estou" com geocodificação reversa (OSM), navegação pro destino (Google Maps), tocar música (YouTube/Spotify), controle de volume |
| 💾 **Memória** | Lembra fatos declarados ("lembra que…"), consulta memórias antigas e mantém contexto entre turnos |
| 🔄 **Auto-update** | Verifica versões novas direto do GitHub e instala por cima — manifesto assinado com Ed25519 |

## 🗂️ Arquitetura (Android)

Projeto nativo em **Kotlin + Jetpack Compose**, um arquivo por responsabilidade:

```
android/app/src/main/java/com/andre/jarvisultra/
├── MainActivity.kt            # Tema + paleta JARVIS OS
├── JarvisScreen.kt            # Tela principal: reator, chat, cabeçalho, settings
├── ArcReactorHud.kt            # O reator: dial, chevrons, blooms, glifo triangular
├── JarvisOsWidgets.kt         # Painéis MEM/NET/GPS/VOZ com dados reais
├── JarvisBrain.kt             # Orquestração de turno, prompt-sistema, histórico
├── GeminiClient.kt            # Chamada à API Gemini (com fallback de modelos)
├── JarvisVosk.kt              # Reconhecimento de voz offline (Vosk pt-BR)
├── JarvisVoice.kt             # Síntese de voz (TTS nativo)
├── JarvisTools.kt             # Tools básicas: memória, timer, busca, calculadora
├── JarvisPhoneTools.kt        # Tools de controle: ligar, WhatsApp, SMS, lanterna…
├── JarvisPercepcao.kt         # Tools de percepção: clima, GPS, navegação, música
├── JarvisVisao.kt             # Visão computacional: tool ver_camera + encode multimodal
├── JarvisNotificationListener.kt + JarvisNotificationStore.kt  # Notificações
├── JarvisMemory.kt           # Memória persistente de fatos
├── SettingsStore.kt          # Chave de API guardada só no aparelho
└── Updater.kt                # Verificação de atualização via GitHub
```

O Gemini recebe as *tools* em cascata (`JarvisTools → JarvisPhoneTools → JarvisPercepcao`) e decide sozinho qual executar em cada ordem.

## 🖥️ Edição Desktop

A raiz do repositório guarda o **JARVIS para desktop** (Python):

- Controle de sistema, arquivos, terminal, visão de tela e webcam
- **v5.0.0+**: modo **Ollama offline** — funciona sem internet nem chave de API
- Interface com temas e kit `.exe` para Windows
- Mesma filosofia: teclado ou voz, memória persistente, botão físico de mudo

```bash
pip install -r requirements.txt
python main.py
```

## 🛠️ Compilar o Android do zero

```bash
cd android
./gradlew :app:assembleRelease
```

Requisitos: JDK 17, Android SDK 34. Assinatura de release via `JARVIS_KEYSTORE` (não incluída no repo).

## 📜 Histórico em resumo

| Versão | Marco |
|---|---|
| **4.5.0** | 👁️ Visão computacional: câmera + multimodal, vê descreve e lê o mundo |
| 4.4.0 | 🎬 Interface JARVIS OS: paleta Stark, núcleo triangular, painéis de dados reais |
| 4.3.x | Reator de arco em Canvas: dial, chevrons, blooms — depois otimizado sem GC churn |
| 4.2.0 | Painel de Configurações: microfone, atualização, sobre |
| 4.1.0 | Gradientes HUD, glassmorphism na barra de entrada |
| 4.0.0 | 🧭 Percepção Total: clima, GPS, navegação, música, contexto vivo no prompt |
| 3.x | 🎙️ Voz offline Vosk pt-BR embutida no APK + mãos-livres com wake word |
| 2.1.x | 📞 Controle Total: ligações, WhatsApp, SMS, notificações, lanterna |
| 2.0.x | 🔧 Tratamento de erros de rede e DNS resiliente |
| 1.0.x | 🚀 Primeiro APK: chat Gemini, voz TTS, updater assinado |

*Versões desktop: 1.0 → 5.0.2 (Ollama offline).*

---

## ⚠️ Licença

Uso pessoal e não comercial — **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**.

## 👤 Autor

**Andre Luiz Lima Menezes** — idealizador, testador e comandante ("senhor") do projeto.

> *"Às ordens, senhor."*
