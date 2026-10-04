"""Reconhecimento de fala (STT).

v4.14.0: o Whisper LOCAL (offline) é o motor preferido — a fala do senhor
vai direto pro modelo pequeno no próprio PC, sem internet. Se o Whisper
não estiver disponível (ou falhar), cai pro reconhecedor do Google online
como reserva. Sem microfone, o botão desabilita — nada quebra.
"""
try:
    import speech_recognition as sr
    DISPONIVEL = True
except Exception:   # ImportError OU OSError (microfone/DLL ausente)
    sr = None
    DISPONIVEL = False


def _transcrever_local(audio) -> str | None:
    """Whisper offline sobre o áudio capturado. Qualquer problema devolve
    None e o chamador usa o Google de reserva."""
    try:
        import os
        import tempfile

        from core import ditado
        ok, _msg = ditado.garantir()
        if not ok:
            return None
        wav = audio.get_wav_data()
        if not wav:
            return None
        fd, caminho = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with open(caminho, "wb") as f:
            f.write(wav)
        try:
            from core import config
            tamanho = config.load().get("whisper_tamanho", ditado.TAMANHO_PADRAO)
            return ditado.transcrever(caminho, tamanho) or None
        finally:
            try:
                os.unlink(caminho)
            except Exception:
                pass
    except Exception:
        return None


def ouvir(frase_de_erro: str = "não te ouvi, senhor. Tente de novo.",
          preferir_local: bool = True) -> str | None:
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
    except Exception:
        return None
    if preferir_local:
        texto = _transcrever_local(audio)
        if texto:
            return texto
    try:
        return recon.recognize_google(audio, language="pt-BR").strip()
    except sr.UnknownValueError:
        return frase_de_erro
    except Exception:
        return None
