"""Diagnóstico de ferramentas (v4.14.0) — o checklist do JARVIS.

Roda em duas famílias:
- EXECUTA de verdade as tools inofensivas (hora, status, memórias, agenda,
  clima...) e vê se devolvem resposta sensata;
- CHECA ESTÁTICAMENTE as que têm efeito colateral (abrir app, tocar música,
  teclas de mídia): verifica o que elas precisam (Windows, chave do Gemini,
  biblioteca instalada) sem disparar nada no PC do senhor.
"""
import importlib.util
import sys


def _tem_lib(modulo: str) -> bool:
    try:
        return importlib.util.find_spec(modulo) is not None
    except Exception:
        return False


def _tem_chave() -> bool:
    try:
        from . import config
        return bool(config.load().get("gemini_api_key", "").strip())
    except Exception:
        return False


def rodar() -> list[tuple[str, bool, str]]:
    """[(nome, ok, detalhe)] — o CONFIG mostra o painel."""
    from . import agenda, tools
    resultados = []

    def executa(nome, args):
        try:
            r = tools.execute(nome, args)
            ruim = ("desconhecida" in r or "erro ao executar" in r
                    or "INVÁLIDOS" in r)
            resultados.append((nome, not ruim, (r[:90] if ruim else "respondendo")))
        except Exception as e:
            resultados.append((nome, False, str(e)[:90]))

    # família 1: executam de verdade (inofensivas)
    executa("hora_agora", {})
    executa("status_do_sistema", {})
    executa("listar_memorias", {})
    executa("listar_agenda", {})
    executa("clima", {})
    executa("onde_estou", {})
    executa("procurar_arquivos", {"nome": "zzz_diagnostico_zzz"})
    executa("definir_timer", {"segundos": 999999, "motivo": "diagnóstico (não dispara)"})

    # família 2: checagem estática (sem efeito colateral)
    resultados.append(("abrir_app / abrir_site / tocar_musica",
                       sys.platform.startswith("win") or sys.platform == "darwin",
                       "pronto no Windows" if sys.platform.startswith("win")
                       else "melhor no Windows — funcionalidade reduzida aqui"))
    resultados.append(("controlar_midia", sys.platform.startswith("win"),
                       "teclas de mídia prontas" if sys.platform.startswith("win")
                       else "só funciona no Windows por enquanto"))
    resultados.append(("controlar_volume", sys.platform.startswith("win"),
                       "pronto no Windows" if sys.platform.startswith("win")
                       else "reduzido fora do Windows"))
    resultados.append(("ver_tela (visão)", _tem_chave(),
                       "chave do Gemini ok" if _tem_chave()
                       else "configure a chave do Gemini no ⚙ pra enxergar a tela"))
    resultados.append(("pesquisar_resumido", True, "busca pronta"
                       + (" + resumo com IA" if _tem_chave() else " (sem chave: só tópicos)")))
    resultados.append(("ler_em_voz_alta", True, "pronta"))
    resultados.append(("ditado por voz (Whisper)", _tem_lib("faster_whisper"),
                       "Whisper instalado" if _tem_lib("faster_whisper")
                       else "instala na 1ª vez que usar o 🎙 (auto-instala)"))
    resultados.append(("bloquear_tela", sys.platform.startswith("win"),
                       "pronto no Windows" if sys.platform.startswith("win")
                       else "via loginctl fora do Windows"))
    resultados.append(("limpar_lixeira", sys.platform.startswith("win"),
                       "pronto no Windows (pede confirmação)" if sys.platform.startswith("win")
                       else "só no Windows"))
    try:
        avisos = len(agenda._load().get("avisos", []))
        resultados.append(("agenda persistente", True, f"{avisos} aviso(s) agendado(s)"))
    except Exception as e:
        resultados.append(("agenda persistente", False, str(e)[:90]))
    return resultados
