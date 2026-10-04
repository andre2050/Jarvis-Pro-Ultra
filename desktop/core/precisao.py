"""Blindagem de precisão (v4.11.0) — valida a chamada ANTES de executar e
avalia o risco das ações.

Duas camadas (a "checagem em 2 passos" do pacote de precisão):

1. valida_chamada: a tool existe? os argumentos obrigatórios vieram? os
   tipos batem com o schema? Se não, devolve um ERRO pro PRÓPRIO MODELO
   (como functionResponse) — ele se corrige na rodada seguinte em vez de
   executar coisa errada, crashar ou inventar parâmetro.

2. avalia_risco: ações irreversíveis ou com efeito externo (apagar/mover
   arquivos, enviar mensagem, controlar mouse/teclado, trocar papel de
   parede) passam pelo core/confirm.py — o modelo NÃO executa sem o
   humano clicar CONFIRMAR na tela.
"""
import json


# ---------- 1. validação de schema ----------

def _tipo_bate(valor, esperado: str) -> bool:
    if esperado == "string":
        return isinstance(valor, str)
    if esperado == "number":
        return isinstance(valor, (int, float)) and not isinstance(valor, bool)
    if esperado == "integer":
        return isinstance(valor, int) and not isinstance(valor, bool)
    if esperado == "boolean":
        return isinstance(valor, bool)
    if esperado == "array":
        return isinstance(valor, (list, tuple))
    if esperado == "object":
        return isinstance(valor, dict)
    return True  # tipo desconhecido: tolera


def valida_chamada(name: str, args, decls: list):
    """None se a chamada está boa; senão, string de erro pro modelo."""
    decl = next((d for d in decls if d.get("name") == name), None)
    if decl is None:
        return (f"a tool '{name}' não existe — use apenas as tools declaradas "
                f"no catálogo de comandos")
    params = decl.get("parameters") or {}
    if not isinstance(params, dict):
        return None
    props = params.get("properties") or {}
    obrigatorios = params.get("required") or []
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return f"os argumentos devem ser um objeto com as chaves {list(props)}"
    for chave in obrigatorios:
        valor = args.get(chave)
        if isinstance(valor, str) and not valor.strip():
            valor = ""
        if valor in (None, "", [], {}):
            desc = (props.get(chave) or {}).get("description", "")
            dica = f" — {desc}" if desc else ""
            return f"falta o argumento obrigatório '{chave}'{dica}"
    for chave, valor in args.items():
        prop = props.get(chave)
        if prop is None:
            continue  # parâmetro extra: tolerado (modelos adicionam e a tool ignora)
        esperado = (prop or {}).get("type")
        if esperado and not _tipo_bate(valor, esperado):
            return (f"o argumento '{chave}' deve ser do tipo {esperado} "
                    f"(recebi {type(valor).__name__})")
        if "enum" in (prop or {}) and valor not in prop["enum"]:
            return f"o argumento '{chave}' deve ser um de: {', '.join(map(str, prop['enum']))}"
    return None


# ---------- 2. termômetro de risco ----------

def avalia_risco(name: str, args) -> tuple | None:
    """(titulo, detalhe) se a ação precisa de confirmação humana; None se
    pode executar direto. Só o GENUINAMENTE irreversível/externo."""
    a = json.dumps(args or {}, ensure_ascii=False, default=str)
    baixa = a.lower()
    if name == "file_controller" and any(
            p in baixa for p in ("delete", "apagar", "trash", "mover", "move",
                                 "rename", "renomear")):
        return "Apagar/mover arquivos", f"file_controller {a[:180]}"
    if name == "send_message":
        return "Enviar mensagem para alguém", f"send_message {a[:180]}"
    if name == "computer_control":
        return "Controlar mouse e teclado", f"computer_control {a[:180]}"
    if name == "desktop" and any(
            p in baixa for p in ("wallpaper", "papel de parede", "fundo de tela")):
        return "Trocar o papel de parede", f"desktop {a[:180]}"
    return None
