"""Cliente do Gemini com function calling real — mesmo protocolo da v4.3.0 Android.

Modo Turbo (v4.0.1): o modelo instantâneo 'gemini-3.5-flash-lite' assume como
titular; se um modelo foi aposentado (404), cai pro próximo; em sobrecarga
(503/429), espera 1s uma vez só e segue.
"""
import json
import time

import requests

# Lista confirmada estável (v3.1.3): rápido primeiro, pensador de reserva
MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


class GeminiHttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class GeminiResult:
    """text pode ser None quando o modelo só pediu tools.

    function_call_parts são as partes CRUAS da resposta que contêm functionCall —
    preservam o campo thoughtSignature (exigido pelos modelos novos ao devolver
    a chamada no histórico). Sempre reenvie a parte inteira como veio.
    """

    def __init__(self, text, function_call_parts, model):
        self.text = text
        self.function_call_parts = function_call_parts
        self.model = model


def turn(api_key: str, system_prompt: str, contents: list, tools: list | None) -> GeminiResult:
    last_error: GeminiHttpError | None = None
    for model in MODELS:
        for attempt in (1, 2):
            try:
                return _call_model(model, api_key, system_prompt, contents, tools)
            except requests.exceptions.ConnectionError:
                if attempt == 2:
                    raise RuntimeError(
                        "⚠️ Sem conexão com a internet, senhor. Verifique a rede e tente de novo."
                    )
                time.sleep(0.8)
            except GeminiHttpError as e:
                if e.status == 404 or "not found" in e.message.lower() or "not supported" in e.message.lower():
                    last_error = e
                    break  # modelo aposentado -> próximo da lista
                if e.status in (503, 429) or "overloaded" in e.message.lower():
                    last_error = e
                    if attempt == 1:
                        time.sleep(1.0)
                        continue
                    break
                raise RuntimeError(e.message)

    base = last_error.message if last_error else ""
    if last_error and last_error.status in (503, 429):
        raise RuntimeError(
            "⚠️ Os servidores do Gemini estão sobrecarregados agora, senhor. Aguarde um minuto e mande de novo."
        )
    raise RuntimeError(base or "Nenhum modelo do Gemini disponível, senhor.")


def _call_model(model: str, api_key: str, system_prompt: str, contents: list, tools: list | None) -> GeminiResult:
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    if tools:
        body["tools"] = [{"function_declarations": tools}]

    resp = requests.post(
        BASE_URL.format(model=model, key=api_key),
        json=body,
        timeout=(20, 60),
        headers={"Content-Type": "application/json"},
    )

    if resp.status_code != 200:
        trecho = resp.text[:220]
        raise GeminiHttpError(resp.status_code, f"HTTP {resp.status_code}: {trecho}")

    data = resp.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        raise GeminiHttpError(500, f"Resposta inesperada do Gemini: {json.dumps(data)[:220]}")

    text = None
    fc_parts = []
    for part in parts:
        if "functionCall" in part:
            fc_parts.append(part)
        elif part.get("text"):
            text = (text or "") + part["text"]
    return GeminiResult(text, fc_parts, model)


def vision(api_key: str, prompt: str, b64: str, mime: str = "image/jpeg") -> str:
    """v4.12.0: uma rodada de VISÃO pura (sem tools, sem histórico) — usada
    pela tool ver_tela pra descrever o print da tela do senhor."""
    for model in MODELS:
        body = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": mime, "data": b64}},
                {"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
        }
        resp = requests.post(BASE_URL.format(model=model, key=api_key), json=body,
                             timeout=(20, 60),
                             headers={"Content-Type": "application/json"})
        if resp.status_code == 404:
            continue  # modelo aposentado: tenta o próximo da lista
        if resp.status_code != 200:
            raise GeminiHttpError(resp.status_code,
                                  f"HTTP {resp.status_code}: {resp.text[:220]}")
        data = resp.json()
        try:
            return (data["candidates"][0]["content"]["parts"][0].get("text")
                    or "").strip()
        except (KeyError, IndexError, TypeError):
            raise GeminiHttpError(500, f"Resposta inesperada do Gemini: {json.dumps(data)[:220]}")
    raise GeminiHttpError(404, "nenhum modelo de visão disponível")


def vision_free(api_key: str, prompt: str) -> str:
    """v4.14.0: rodada de texto puro sem imagem e sem tools — usada pelo
    resumo inteligente da busca (mesma cadeia de modelos do chat)."""
    for model in MODELS:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
        }
        resp = requests.post(BASE_URL.format(model=model, key=api_key), json=body,
                             timeout=(20, 60),
                             headers={"Content-Type": "application/json"})
        if resp.status_code == 404:
            continue
        if resp.status_code != 200:
            raise GeminiHttpError(resp.status_code,
                                  f"HTTP {resp.status_code}: {resp.text[:220]}")
        data = resp.json()
        try:
            return (data["candidates"][0]["content"]["parts"][0].get("text")
                    or "").strip()
        except (KeyError, IndexError, TypeError):
            raise GeminiHttpError(500, f"Resposta inesperada do Gemini: {json.dumps(data)[:220]}")
    raise GeminiHttpError(404, "nenhum modelo disponível")
