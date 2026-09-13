"""Reconhecimento de fala (STT) — opcional.

Usa a biblioteca 'speech_recognition' (reconhecedor do Google, online).
Se não estiver instalada (ou não houver microfone), o botão de microfone
fica desabilitado — nada quebra.
"""
try:
    import speech_recognition as sr
    DISPONIVEL = True
except ImportError:
    sr = None
    DISPONIVEL = False


def ouvir(frase_de_erro: str = "não te ouvi, senhor. Tente de novo.") -> str | None:
    """Escuta UMA frase e devolve o texto (ou None)."""
    if not DISPONIVEL:
        return None
    recon = sr.Recognizer()
    recon.energy_threshold = 300
    recon.dynamic_energy_threshold = True
    try:
        with sr.Microphone() as mic:
            recon.adjust_for_ambient_noise(mic, duration=0.4)
            audio = recon.listen(mic, timeout=6, phrase_time_limit=12)
        texto = recon.recognize_google(audio, language="pt-BR")
        return texto.strip()
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return frase_de_erro
    except Exception:
        return None
