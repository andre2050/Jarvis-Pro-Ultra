# 🤖 J.A.R.V.I.S — Pro Ultra Desktop v4.3.0 — Reator de Arco Vermelho

O JARVIS da v4.3.0 do Android, agora no seu computador — 100% Python.

Interface: o **reator de arco do Homem de Ferro** — dial circular vermelho
com marcações de instrumento, blooms de luz pulsantes, anel de chevrons
girando (acelera no modo mãos-livres), grade radial e o núcleo com a
leitura viva do computador (bateria no laptop ou CPU no desktop, hora e
data, ao vivo).

## ✨ O que ele faz

| Módulo | Descrição |
|---|---|
| 🧠 Cérebro Gemini | Function calling real, com lista de modelos estáveis e Modo Turbo (v4.0.1) |
| 🎙️ Voz | Fala em voz alta (TTS offline) e escuta comandos (STT, opcional). **F4** liga/desliga a voz |
| 👁️ Percepção Total | Clima em tempo real (Open-Meteo), onde você está (IP), rota no mapa |
| 🖥️ Status do sistema | CPU, RAM, bateria e disco — injetados no cérebro a cada turno |
| 📦 Tools | Música no YouTube, volume, abrir apps/sites, busca web, timer, memória de longo prazo |
| ⚙️ Configurações | Chave do Gemini (com teste), voz, verificação de atualização no GitHub, sobre |
| 💾 Memória | Guarda fatos a seu pedido em `~/.jarvis_pro_ultra/memory.json` |

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python main.py
```

> Se der `ModuleNotFoundError` em algum opcional (pyaudio, pycaw…),
> instale só o que faltar — nada quebra sem eles.

Depois:
1. Clique em **⚙ CONFIG** (canto superior direito)
2. Cole sua **chave do Gemini** — grátis em https://aistudio.google.com
3. Clique em **Salvar e Testar** — o mordomo acorda

## 🎙️ Mão na massa

- Digite ou fale: *"qual o tempo agora?"*, *"toca Iron Maiden"*,
  *"onde estou?"*, *"me leva até o mercado"*, *"lembra que o aniversário
  da Ana é dia 20"*, *"status do sistema"*, *"timer de 5 minutos pro macarrão"*
- **F4** — liga/desliga a voz (privacidade em um toque)
- Teste de voz nas configurações: *"Good evening. All systems are online
  and operating at full capacity."*

## 📁 Estrutura

```
main.py              — janela principal (reator + chat + entrada)
core/
  brain.py           — persona + loop de function calling
  gemini_client.py   — Gemini com fallback de modelos e retry enxuto
  tools.py           — 13 tools de desktop (clima, música, volume, memória…)
  perception.py      — contexto vivo do computador
  memory.py          — memória de longo prazo
  config.py          — ~/.jarvis_pro_ultra/config.json
  updater.py         — consulta releases no GitHub
voice/
  tts.py             — voz offline (fila dedicada)
  stt.py             — reconhecimento de fala (opcional)
ui/
  reactor.py         — o reator de arco animado (porte do ArcReactorHud.kt)
  chat.py            — bolhas estilo v4.1.0 'Elegância'
  settings.py        — painel de configurações (v4.2.0)
```

## ⚠️ Licença
Uso pessoal e não comercial — CC BY-NC 4.0, mesma do projeto original.

---
**André Luiz Lima Menezes** — baseado no [Jarvis-Pro-Ultra](https://github.com/andre2050/Jarvis-Pro-Ultra) v4.3.0
