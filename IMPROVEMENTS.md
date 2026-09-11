# JARVIS — Registro de melhorias (v1.0.0)

Arquitetura aprimorada do assistente. Esta versão acompanha o `main.py` revisado.

## 1. Registry de tools (extensível)

Antes: `_execute_tool` tinha um `if/elif` gigante — adicionar tool nova
exigia mexer no coração do loop.

Agora: todas as tools comuns ficam em `_build_tool_handlers()` (main.py),
num dicionário simples. **Adicionar tool nova = 1 linha.**
Na inicialização, o JARVIS cruza `tools_manifest.py` com o registry e
avisa no log se alguma tool declarada ao Gemini ficou sem handler.

## 2. Configuração central (`config/settings.json`)

Nada mais hardcoded em código:

| Chave | O que controla |
|---|---|
| `model` | Modelo Gemini (trocável quando sair modelo novo) |
| `voice` | Voz (Charon, Puck, etc.) |
| `language` | Idioma preferido — injetado no prompt do sistema |
| `tool_timeout_seconds` | Tempo máximo de cada tool antes de desistir |
| `max_reconnect_delay_seconds` | Teto do backoff de reconexão |
| `manifest_url` | URL do update.json (vazio = checagem desativada) |

Se o arquivo não existir, o JARVIS cria com os defaults na primeira execução.

## 3. Logging com arquivo rotativo (`logs/jarvis.log`)

- Console continua igual (pra acompanhar ao vivo)
- Novo: arquivo `logs/jarvis.log` com data/hora, rotação a cada 1 MB
  (mantém 3 anteriores)
- Essencial quando o JARVIS rodar em máquinas de outras pessoas —
  você pede o log e diagnostica sem estar na frente
- Todos os `print` do main.py agora são `log.info`

## 4. Sistema de versão + aviso de update integrado

- `version.py` mantém `__version__ = "1.0.0"` (incrementa a cada release)
- Na conexão, o JARVIS consulta `manifest_url` em background (thread
  separada, sem travar o áudio). Se houver versão nova, ele **fala**:
  "Sir, version 1.1.0 is now available"
- A instalação do update continua sendo responsabilidade do launcher
  (nunca se atualiza com o app rodando)
- Com `manifest_url` vazio, a checagem fica desativada

## 5. Robustez (da revisão anterior)

- Fila de áudio: chunk descartado quando o buffer enche (sem QueueFull)
- Timeout em todas as tools (default 90s, configurável)
- Backoff de reconexão: 3s → 6s → 12s → 24s → teto configurável;
  chave de API inválida = avisa na UI e espera 60s
- `asyncio.get_running_loop()` no lugar do deprecado `get_event_loop()`

## 6. Suporte a idioma

`language: "pt-BR"` no settings injeta a instrução de idioma no prompt —
o JARVIS responde no idioma do usuário sem reescrever o prompt.txt.

## Arquivos novos

- `tools_manifest.py` — 19 declarações de tools
- `config/settings.json` — configuração central
- `core/settings.py` — carregador (cria o JSON com defaults se faltar)
- `core/logger.py` — logging rotativo
- `updater.py` — checagem de versão online
- `version.py` — versão atual

## 7. Assinatura digital dos updates (fail closed)

O manifesto `update.json` agora deve ser assinado com a chave privada
Ed25519 (`jarvis-updater/sign_release.py`). O JARVIS verifica com
`keys/ed25519_public.pem` antes de anunciar update; o launcher do kit
exige assinatura válida antes de instalar. Manifestos sem assinatura ou
adulterados são RECUSADOS — nem servidor invadido consegue empurrar
código malicioso sem sua chave privada.

`cryptography>=42.0` adicionado ao requirements.txt.

## Checklist pra distribuir

1. `config/api_keys.json` NUNCA vai dentro do zip de release
2. Excluir `__pycache__/` e `logs/` antes de zipar
3. Incrementar `version.py`
4. Zipar, gerar `sha256sum`, subir e atualizar o `update.json`
