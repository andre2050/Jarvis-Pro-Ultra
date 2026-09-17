# J.A.R.V.I.S Ultra — iOS (v4.7.1)

A mesma experiência do Android, agora nativa em **SwiftUI**: o radar holográfico
teal com agulha vermelha, cérebro Gemini, voz britânica (en-GB, pitch 0.8) e
verificador de atualização.

## O que tem nesta v1 iOS

- 🛰 **RadarHud (SwiftUI Canvas)** — holograma circular teal `0x00E5C7`, agulha
  vermelha varrendo (acelera quando pensa/fala), anéis, retículo, blips
  cintilantes, bateria/hora/data do aparelho dentro do holograma
- 🧠 **Cérebro Gemini** — a mesma cadeia de modelos do Android
  (`gemini-3.5-flash-lite → gemini-3.6-flash → gemini-2.5-flash → gemini-2.5-flash-lite`)
- 🗣 **Voz de mordomo** — motor nativo do iOS (AVSpeechSynthesizer), en-GB,
  pitch 0.8, velocidade ~0.85, zero dependências
- ⚙ **CONFIG** — chave do Gemini (guardada no aparelho), "Testar voz"
  (*"Good evening. All systems are online and operating at full capacity."*)
  e verificador de atualização
- 🔄 **Updater** — consulta as releases do GitHub (no iOS a instalação é pela
  página de releases; a Apple não permite atualizar app por dentro do app)

**Ainda não nesta v1**: ouvir sua voz (STT offline tipo o Vosk) e function
calling com ferramentas. São os próximos passos.

## Como rodar no seu iPhone

> ⚠️ Compilar app iOS exige um **Mac com Xcode** (gratuito na App Store).
> Não existe build de iOS fora da Apple — é limitação do ecossistema, não do projeto.

1. **No Mac**: clone o repositório e abra `ios/JarvisUltra.xcodeproj` no Xcode
   (precisa do Xcode 16 ou mais novo)
2. **Assinatura**: na aba *Signing & Capabilities*, marque *Automatically manage
   signing* e escolha seu Apple ID gratuito (Xcode → Settings → Accounts → +)
3. **Conecte o iPhone** por cabo, selecione ele no menu de dispositivos do Xcode
4. No iPhone: **Ajustes → Privacidade e Segurança → Modo de Desenvolvedor** →
   ligar (o Xcode pede isso na primeira vez)
5. **⌘R** — o JARVIS instala e abre no aparelho
6. Abra o ⚙ no app e cole sua chave Gemini (`AIza...`, de aistudio.google.com)

### Sem a conta paga da Apple (US$ 99/ano)

Com o Apple ID **gratuito**, o app instalado expira a cada **7 dias** — o Xcode
só assina por esse período. Basta plugar o iPhone e apertar ⌘R de novo quando
expirar. Com a conta paga, vale 1 ano e você pode distribuir via TestFlight.

### Sem Mac?

Dá pra compilar na nuvem (ex.: **Codemagic**, que tem plano free e conecta no
GitHub), mas a assinatura continua exigindo Apple ID — e o perfil free de 7 dias
também se aplica. O Mac é o caminho mais simples.

## Estrutura

```
ios/
├── JarvisUltra.xcodeproj/   ← projeto Xcode (grupo sincronizado: compila tudo de JarvisUltra/)
└── JarvisUltra/
    ├── JarvisUltraApp.swift ← entry point
    ├── ContentView.swift   ← radar + chat + campo de mensagem
    ├── RadarHud.swift       ← o radar holográfico (Canvas + TimelineView)
    ├── Brain.swift          ← cliente Gemini com cadeia de fallback
    ├── Speech.swift         ← voz en-GB do mordomo
    ├── SettingsView.swift   ← ⚙ CONFIG (chave, teste de voz, atualização)
    └── Updater.swift        ← verificador de versão via GitHub releases
```
