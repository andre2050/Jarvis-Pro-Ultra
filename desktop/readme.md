# 🤖 J.A.R.V.I.S — Pro Ultra Desktop v4.4.0
## Reator de Arco Vermelho × Mark LIII

A fusão: a interface **Reator de Arco Vermelho** da v4.3.0 com o arsenal do
[Mark LIII](https://github.com/FatihMakes) — **rede neural de wake word local**,
16 ações auto-descritivas, undo real e confirmação que o modelo não forja.

> ⚠️ **Update da v4.3.0**: se já usava a v4.3.0, só rodar por cima — suas
> memórias e configurações (`~/.jarvis_pro_ultra`) continuam valendo.

## ✨ O que entrou de novo (v4.4.0)

| Módulo | Descrição |
|---|---|
| 🧠 **Wake Word "Hey Jarvis"** | Rede neural local (openwakeword/ONNX, ~5 MB, offline). Fale "Hey Jarvis" e ele escuta o comando — nada sai do seu microfone antes do disparo. Instala em 1 clique em ⚙ CONFIG |
| 🧩 **Ações auto-descritivas** | Sistema do Mark LIII: cada `actions/*.py` se descreve e é descoberto no boot — adicionar skill é largar um arquivo |
| 📂 **File Processor / Controller** | Ler, resumir e responder perguntas sobre arquivos; mover/renomear com proteção |
| 💻 **Code Helper & Dev Agent** | Revisão inline de código e agente de desenvolvimento |
| 🌐 **Browser Control** | Controle de navegador por voz (Playwright) |
| 📨 **Send Message** | WhatsApp, Telegram e afins via webhook/URL |
| 🖥️ **System & Desktop Control** | Monitor de hardware, janelas, atalhos, configurações, energia |
| ↩️ **Undo real** | Desfaz arquivos movidos/criados/renomeados e configurações ("desfaz a última ação") |
| ⚠️ **Confirmação com botão humano** | Desligar, reiniciar e ações irreversíveis esperam VOCÊ apertar — o modelo não pode forjar |
| ⏰ **Reminders nativos** | Lembretes via sistema (Task Scheduler / LaunchAgent / systemd) |
| ✈️🎮 **Flight Finder & Game Updater** | Passagens ao vivo e updates de Steam/Epic |
| 🎬 **YouTube avançado** | Busca, transcrição e controle de reprodução |

E tudo da v4.3.0 continua: reator animado, cérebro Gemini com function calling
+ Modo Turbo, 14 tools nativas (clima real via Open-Meteo, onde estou, música,
volume, timer, memória de longo prazo…), voz pt-BR e painel de configurações.

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python main.py
```

1. **⚙ CONFIG** → cole sua chave do Gemini (grátis em https://aistudio.google.com) → **Salvar e Testar**
2. (opcional) **⚙ CONFIG → WAKE WORD → Instalar agora** → depois **🧠 HEY JARVIS** na barra superior
3. Fale ou digite. Exemplos: *"resuma o arquivo contrato.pdf"*, *"Hey Jarvis, qual o clima em Recife?"*,
   *"abre o Chrome"*, *"pesquisa preços de RTX 5090"*, *"desfaz a última ação"*

## 📁 Estrutura

```
main.py                  — janela, registro de ações, wake word, confirmação
core/
  brain.py               — persona + loop de function calling (nativas + Mark LIII)
  action_loader.py       — descoberta automática de ações (do Mark LIII)
  adapters.py            — liga as ações ao nosso app (log, voz, sessão)
  wake_word.py           — rede neural local "Hey Jarvis" (do Mark LIII)
  confirm.py / undo.py   — confirmação humana + pilha de desfazer (do Mark LIII)
  gemini_client.py / tools.py / perception.py / memory.py — núcleo v4.3.0
actions/                 — 16 ações auto-descritivas (do Mark LIII)
voice/                   — TTS, STT e escuta neural contínua
ui/                      — reator de arco, chat e configurações
config/                  — helpers de SO + api_keys.json (formato Mark LIII)
```

## 📄 Licenças

- Projeto original: CC BY-NC 4.0 (uso pessoal e não comercial)
- Módulos do Mark LIII (FatihMakes): CC BY-NC 4.0 — ver `LICENSE-MARK-LIII`

---
**André Luiz Lima Menezes** — [Jarvis-Pro-Ultra](https://github.com/andre2050/Jarvis-Pro-Ultra)
