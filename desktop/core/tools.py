"""As tools do JARVIS desktop — function calling real, mesmas do Android v4.3.0
adaptadas ao computador: percepção (clima, onde estou, navegação), música,
volume, apps, sites, busca, memória e timer.
"""
import os
import platform
import subprocess
import threading
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus

import requests

from . import agenda, gemini_client, memory

# ---------- callback opcional (o app registra para avisar quando o timer dispara) ----------
on_timer_fire = None


# v4.12.0: ver_tela precisa da chave do Gemini — main.py liga no boot
_cfg: dict = {}


def set_cfg(cfg: dict) -> None:
    global _cfg
    _cfg = cfg


def avisa_timer(motivo: str):
    if on_timer_fire:
        try:
            on_timer_fire(motivo)
        except Exception:
            pass


# ==================== DECLARAÇÕES (protocolo Gemini v1beta) ====================

def _decl(nome, desc, params=None):
    params = params or {"type": "object", "properties": {}}
    return {"name": nome, "description": desc, "parameters": params}


def declarations() -> list:
    return [
        _decl("hora_agora", "Informa a hora e a data atuais do computador."),
        _decl("status_do_sistema", "Lê o status do computador: uso de CPU, memória RAM, bateria e disco."),
        _decl("clima", "Clima em tempo real (Open-Meteo, sem chave). Sem cidade, usa a localização aproximada por IP.",
              {"type": "object", "properties": {"cidade": {"type": "string", "description": "Cidade para o clima (opcional)"}}}),
        _decl("onde_estou", "Localização aproximada por IP: cidade, região e país."),
        _decl("navegar_para", "Abre o mapa com a rota até o destino no navegador.",
              {"type": "object", "properties": {"destino": {"type": "string", "description": "Endereço ou nome do lugar"}}, "required": ["destino"]}),
        _decl("tocar_musica", "Toca música: abre a busca no YouTube no navegador.",
              {"type": "object", "properties": {"busca": {"type": "string", "description": "Música, artista ou playlist"}}, "required": ["busca"]}),
        _decl("controlar_volume", "Controla o volume do computador: aumentar, diminuir, silenciar ou máximo. Sem argumentos, informa o volume atual.",
              {"type": "object", "properties": {"acao": {"type": "string", "enum": ["aumentar", "diminuir", "silenciar", "maximo"], "description": "Ação de volume desejada (opcional)"}}}),
        _decl("pesquisar_web", "Pesquisa na web (DuckDuckGo) e devolve títulos e resumos dos principais resultados.",
              {"type": "object", "properties": {"busca": {"type": "string", "description": "Termo da pesquisa"}}, "required": ["busca"]}),
        _decl("abrir_site", "Abre um site no navegador padrão.",
              {"type": "object", "properties": {"url": {"type": "string", "description": "URL do site"}}, "required": ["url"]}),
        _decl("abrir_app", "Abre um aplicativo do computador (ex: bloco de notas, calculadora, explorador, terminal).",
              {"type": "object", "properties": {"app": {"type": "string", "description": "Nome do aplicativo"}}, "required": ["app"]}),
        _decl("lembrar_fato", "Guarda um fato na memória de longo prazo sobre o usuário.",
              {"type": "object", "properties": {"fato": {"type": "string", "description": "O fato a ser memorizado"}}, "required": ["fato"]}),
        _decl("listar_memorias", "Lista as memórias de longo prazo guardadas."),
        _decl("definir_timer", "Define um timer/lembrete que avisa com mensagem e voz quando o tempo acaba.",
              {"type": "object", "properties": {"segundos": {"type": "number", "description": "Duração em segundos"}, "motivo": {"type": "string", "description": "Motivo do timer (opcional)"}}, "required": ["segundos"]}),
        _decl("desfazer_ultima_acao", "Desfaz a ação reversível mais recente (arquivos movidos/renomeados/criados/editados, configurações alteradas)."),
        _decl("agendar_aviso", "Agenda um aviso persistente: dispara com voz e mensagem na hora marcada, MESMO se o app só abrir depois (salvo em disco). Formatos: '18:30' (hoje, ou amanhã se já passou), 'amanhã 08:00', '05/12 09:00', '05/12/2026 09:00' ou '2026-12-05T09:00'.",
              {"type": "object", "properties": {"horario": {"type": "string", "description": "Quando avisar, ex: '18:30' ou 'amanhã 08:00'"}, "motivo": {"type": "string", "description": "O que avisar na hora marcada"}}, "required": ["horario", "motivo"]}),
        _decl("listar_agenda", "Lista os avisos agendados com seus ids."),
        _decl("cancelar_aviso", "Cancela um aviso agendado pelo id (veja em listar_agenda).",
              {"type": "object", "properties": {"id": {"type": "number", "description": "Id do aviso em listar_agenda"}}, "required": ["id"]}),
        _decl("ver_tela", "Lê a tela do computador: tira um print e descreve/transcreve o que está nela (erro, texto, janela). Requer o cérebro na nuvem com chave válida.",
              {"type": "object", "properties": {"pergunta": {"type": "string", "description": "O que observar ou responder sobre a tela (opcional)"}}}),
        _decl("procurar_arquivos", "Procura arquivos no PC por nome (ou parte dele) nas pastas do usuário (Desktop, Documentos, Downloads, Imagens, Músicas, Vídeos) e devolve até 10 resultados com o caminho completo. Use quando o senhor perguntar 'onde está o arquivo X'.",
              {"type": "object", "properties": {"nome": {"type": "string", "description": "Nome ou parte do nome do arquivo"}, "pasta": {"type": "string", "enum": ["todas", "desktop", "documentos", "downloads", "imagens", "musicas", "videos"], "description": "Onde procurar (opcional; padrão: todas)"}}, "required": ["nome"]}),
        _decl("controlar_midia", "Controla o player de mídia do PC (o que estiver tocando: Spotify, YouTube no navegador, Media Player): play/pause, próxima faixa ou faixa anterior.",
              {"type": "object", "properties": {"acao": {"type": "string", "enum": ["play_pause", "proxima", "anterior"], "description": "Ação do player"}}, "required": ["acao"]}),
    ]


# ==================== EXECUÇÃO ====================

def nomes() -> set:
    """Nomes das tools nativas (usado pra reservar nomes no registro de ações)."""
    return {"hora_agora", "status_do_sistema", "clima", "onde_estou", "navegar_para",
            "tocar_musica", "controlar_volume", "pesquisar_web", "abrir_site",
            "abrir_app", "lembrar_fato", "listar_memorias", "definir_timer",
            "desfazer_ultima_acao", "agendar_aviso", "listar_agenda",
            "cancelar_aviso", "ver_tela", "procurar_arquivos",
            "controlar_midia"}


def execute(name: str, args: dict) -> str:
    fn = {
        "hora_agora": lambda: _hora(),
        "status_do_sistema": lambda: _status(),
        "clima": lambda: _clima(args.get("cidade")),
        "onde_estou": lambda: _onde_estou(),
        "navegar_para": lambda: _navegar(args.get("destino", "")),
        "tocar_musica": lambda: _musica(args.get("busca", "")),
        "controlar_volume": lambda: _volume(args.get("acao")),
        "pesquisar_web": lambda: _pesquisar(args.get("busca", "")),
        "abrir_site": lambda: _site(args.get("url", "")),
        "abrir_app": lambda: _app(args.get("app", "")),
        "lembrar_fato": lambda: memory.lembrar(args.get("fato", "")),
        "listar_memorias": lambda: memory.listar(),
        "definir_timer": lambda: _timer(args.get("segundos", 60), args.get("motivo", "")),
        "desfazer_ultima_acao": _desfazer,
        "agendar_aviso": lambda: agenda.agendar(args.get("horario", ""), args.get("motivo", "")),
        "listar_agenda": lambda: agenda.listar(),
        "cancelar_aviso": lambda: agenda.cancelar(args.get("id", 0)),
        "ver_tela": lambda: _ver_tela(args.get("pergunta", "")),
        "procurar_arquivos": lambda: _procurar_arquivos(args.get("nome", ""), args.get("pasta", "todas")),
        "controlar_midia": lambda: _controlar_midia(args.get("acao", "play_pause")),
    }.get(name)
    if fn is None:
        return f"tool desconhecida: {name}"
    try:
        return fn()
    except Exception as e:
        return f"erro ao executar '{name}': {e}"


# ==================== IMPLEMENTAÇÕES ====================

def _hora() -> str:
    agora = datetime.now()
    dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]
    return (f"São {agora.strftime('%H:%M')} de {agora.day} de {meses[agora.month - 1]} de {agora.year}, "
            f"{dias[agora.weekday()]}.")


def _status() -> str:
    import psutil
    cpu = psutil.cpu_percent(interval=0.4)
    mem = psutil.virtual_memory()
    disco = psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:\\").percent
    linhas = [f"CPU em {cpu:.0f}%",
              f"RAM em {mem.percent:.0f}% de {round(mem.total / 1024**3)} GB",
              f"Disco em {disco:.0f}%"]
    try:
        bat = psutil.sensors_battery()
        if bat:
            linhas.append(f"Bateria em {round(bat.percent)}% ({'carregando' if bat.power_plugged else 'na bateria'})")
    except Exception:
        pass
    return "Status do computador: " + ", ".join(linhas) + "."


def _geo_ip() -> dict | None:
    """Localização aproximada por IP — tenta três serviços, o que responder primeiro vale."""
    tentativas = (
        ("https://ipapi.co/json/",
         lambda d: {"lat": d.get("latitude"), "lon": d.get("longitude"),
                    "cidade": d.get("city"), "regiao": d.get("region"), "pais": d.get("country_name")}),
        ("https://ipinfo.io/json",
         lambda d: {"lat": float(d["loc"].split(",")[0]), "lon": float(d["loc"].split(",")[1]),
                    "cidade": d.get("city"), "regiao": d.get("region"), "pais": d.get("country")}),
        ("https://ipwho.is/",
         lambda d: {"lat": d.get("latitude"), "lon": d.get("longitude"),
                    "cidade": d.get("city"), "regiao": d.get("region"), "pais": d.get("country")}),
    )
    for url, extrai in tentativas:
        try:
            d = requests.get(url, timeout=8).json()
            geo = extrai(d)
            if geo.get("lat") is not None and geo.get("cidade"):
                return geo
        except Exception:
            continue
    return None


def _geocode(cidade: str) -> dict | None:
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": cidade, "count": 1, "language": "pt"},
            timeout=8,
        )
        res = r.json().get("results") or []
        if res:
            g = res[0]
            return {"lat": g.get("latitude"), "lon": g.get("longitude"),
                    "cidade": g.get("name"), "regiao": g.get("admin1"), "pais": g.get("country")}
    except Exception:
        pass
    return None


def _clima(cidade: str | None) -> str:
    geo = _geocode(cidade) if cidade else _geo_ip()
    if not geo or geo.get("lat") is None:
        return "não consegui obter a localização, senhor."
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": geo["lat"], "longitude": geo["lon"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
            },
            timeout=10,
        )
        c = r.json()
        cur = c["current"]
        dia = c["daily"]
        lugar = geo.get("cidade") or cidade
        return (f"Clima agora em {lugar}: {cur['temperature_2m']}°C (sensação de "
                f"{cur['apparent_temperature']}°C), umidade {cur['relative_humidity_2m']}%, "
                f"vento {cur['wind_speed_10m']} km/h. Mínima de {dia['temperature_2m_min'][0]}°C "
                f"e máxima de {dia['temperature_2m_max'][0]}°C hoje.")
    except Exception as e:
        return f"falha ao consultar o clima: {e}"


def _onde_estou() -> str:
    geo = _geo_ip()
    if not geo:
        return "não consegui localizar pela rede, senhor."
    return f"Pela sua conexão, você está em {geo.get('cidade')}, {geo.get('regiao')} — {geo.get('pais')}."


def _navegar(destino: str) -> str:
    if not destino:
        return "destino em branco, senhor."
    webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(destino)}")
    return f"rota até {destino} aberta no navegador, senhor."


def _musica(busca: str) -> str:
    if not busca:
        return "o quê devo tocar, senhor?"
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(busca)}")
    return f"YouTube aberto com a busca de '{busca}', senhor. Bom show."


def _volume(acao: str | None) -> str:
    sistema = platform.system()

    if sistema == "Windows":
        return _volume_windows(acao)
    if sistema == "Darwin":
        return _volume_mac(acao)
    return _volume_linux(acao)


def _volume_windows(acao: str | None) -> str:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        dev = AudioUtilities.GetSpeakers()
        interface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        atual = vol.GetMasterVolumeLevelScalar()
        if not acao:
            return f"volume em {round(atual * 100)}%, senhor."
        alvo = {"aumentar": min(1.0, atual + 0.1), "diminuir": max(0.0, atual - 0.1),
                "silenciar": 0.0, "maximo": 1.0}[acao]
        vol.SetMasterVolumeLevelScalar(alvo, None)
        return f"volume agora em {round(alvo * 100)}%, senhor."
    except ImportError:
        return ("para controle fino de volume, instale 'pycaw' (pip install pycaw comtypes), "
                "senhor — ou use as teclas de mídia do teclado.")


def _volume_mac(acao: str | None) -> str:
    import subprocess as sp
    atual = int(sp.check_output(["osascript", "-e", "output volume of (get volume settings)"]).split()[1])
    if not acao:
        return f"volume em {atual}%, senhor."
    alvo = {"aumentar": min(100, atual + 10), "diminuir": max(0, atual - 10),
            "silenciar": 0, "maximo": 100}[acao]
    sp.run(["osascript", "-e", f"set volume output volume {alvo}"], check=False)
    return f"volume agora em {alvo}%, senhor."


def _volume_linux(acao: str | None) -> str:
    import subprocess as sp
    if not acao:
        return "use alsamixer no terminal para ver o volume, senhor."
    passo = {"aumentar": "10%+", "diminuir": "10%-", "silenciar": "0", "maximo": "100%"}[acao]
    for cmd in (["amixer", "-D", "pulse", "sset", "Master", passo],
                ["amixer", "sset", "Master", passo]):
        try:
            sp.run(cmd, capture_output=True, timeout=5)
            return f"volume {acao} feito, senhor."
        except Exception:
            continue
    return "não encontrei o alsamixer neste sistema, senhor."


def _pesquisar(busca: str) -> str:
    if not busca:
        return "o quê devo pesquisar, senhor?"
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            res = list(ddgs.text(busca, max_results=5, region="br-pt"))
        if not res:
            return f"nada encontrado para '{busca}', senhor."
        linhas = [f"- {r['title']}: {r['body'][:150]}" for r in res]
        return f"Resultados para '{busca}':\n" + "\n".join(linhas)
    except ImportError:
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(busca)}")
        return "abri a busca no navegador, senhor (instale 'duckduckgo-search' para eu ler os resultados)."


def _site(url: str) -> str:
    if not url:
        return "url em branco, senhor."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"{url} aberto, senhor."


APPS_WINDOWS = {
    "bloco de notas": "notepad.exe", "notepad": "notepad.exe",
    "calculadora": "calc.exe", "explorador": "explorer.exe",
    "explorador de arquivos": "explorer.exe", "paint": "mspaint.exe",
    "configurações": "ms-settings:", "terminal": "cmd.exe",
    "prompt": "cmd.exe", "powershell": "powershell.exe",
    "gerenciador de tarefas": "taskmgr.exe", "word": "winword.exe",
    "excel": "excel.exe", "chrome": "chrome.exe", "edge": "msedge.exe",
}
APPS_LINUX = {"terminal": "x-terminal-emulator", "arquivos": "nautilus",
              "calculadora": "gnome-calculator", "bloco de notas": "gedit"}
APPS_MAC = {"terminal": "Terminal", "calculadora": "Calculator",
            "arquivos": "Finder", "bloco de notas": "TextEdit"}


def _app(app: str) -> str:
    if not app:
        return "qual app, senhor?"
    chave = app.strip().lower()
    sistema = platform.system()
    try:
        if sistema == "Windows":
            alvo = APPS_WINDOWS.get(chave, chave)
            subprocess.Popen(f"start {alvo}", shell=True)
        elif sistema == "Darwin":
            alvo = APPS_MAC.get(chave, chave).replace(" ", "\\ ")
            subprocess.Popen(["open", "-a", APPS_MAC.get(chave, chave)])
        else:
            alvo = APPS_LINUX.get(chave, chave)
            subprocess.Popen([alvo])
        return f"abrindo {app}, senhor."
    except Exception as e:
        return f"não consegui abrir '{app}': {e}"


def _desfazer() -> str:
    from .undo import undo_last
    return undo_last()


def _timer(segundos, motivo: str) -> str:
    try:
        segundos = max(1, int(segundos))
    except (TypeError, ValueError):
        segundos = 60
    def dispara():
        import time as _t
        _t.sleep(segundos)
        avisa_timer(motivo or "timer")
    threading.Thread(target=dispara, daemon=True).start()
    if segundos >= 60:
        tempo = f"{segundos // 60} min" if segundos % 60 == 0 else f"{segundos / 60:.1f} min"
    else:
        tempo = f"{segundos} s"
    return f"timer de {tempo} definido{', para ' + motivo if motivo else ''}, senhor. Eu aviso."


# ==================== VISÃO DE TELA (v4.12.0) ====================

def _ver_tela(pergunta: str) -> str:
    """Tira um print da tela e pede pro Gemini descrever/ler. Sem chave ou
    no modo offline, avisa na cara — nunca falha em silêncio."""
    if not _cfg.get("gemini_api_key"):
        return ("A visão de tela funciona no cérebro ☁ NUVEM, senhor — configure "
                "a chave do Gemini no ⚙ CONFIG e tente de novo.")
    try:
        import base64
        import io
        from PIL import Image
        img = None
        try:
            from PIL import ImageGrab
            try:
                import mss
                with mss.mss() as s:
                    quadro = s.grab(s.monitors[0])
                    img = Image.frombytes("RGB", (quadro.width, quadro.height),
                                          quadro.bgra, "raw", "BGRX")
            except Exception:
                img = ImageGrab.grab()
        except Exception:
            return "não consegui acessar a captura de tela (Pillow), senhor."
        if img is None:
            return "não consegui capturar a tela, senhor."
        img.thumbnail((1280, 1280))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        prompt = ("Você é o JARVIS. Isto é um print da tela do computador do André. "
                  "Descreva objetivamente: janelas abertas, textos principais e "
                  "qualquer erro visível. Responda em português do Brasil, curto "
                  "e direto. " + (f"Pergunta dele: {pergunta}" if pergunta else "")).strip()
        return gemini_client.vision(_cfg["gemini_api_key"], prompt, b64)
    except Exception as e:
        return f"não consegui enxergar a tela, senhor: {e}"


# ==================== BUSCA DE ARQUIVOS (v4.13.0) ====================

def _pastas_usuario() -> dict:
    from pathlib import Path
    home = Path.home()
    return {
        "desktop": home / "Desktop",
        "documentos": home / "Documents",
        "downloads": home / "Downloads",
        "imagens": home / "Pictures",
        "musicas": home / "Music",
        "videos": home / "Videos",
    }


def _norm_txt(t: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFD", (t or "").lower()).encode(
        "ascii", "ignore").decode()


def _procurar_arquivos(nome: str, pasta: str = "todas") -> str:
    """Procura por nome (sem acento/caixa) nas pastas do usuário, com
    timeout de segurança pra não varrer o PC inteiro."""
    import os
    import time as _t
    from pathlib import Path
    alvo = _norm_txt(nome)
    if not alvo:
        return "diga o nome (ou parte dele) do arquivo, senhor."
    pastas = _pastas_usuario()
    if pasta in pastas:
        bases = [pastas[pasta]]
    else:
        bases = [p for p in pastas.values() if p.exists()]
    achados = []
    limite = _t.time() + 3.5  # teto de varredura: 3,5s
    for base in bases:
        if not base.exists():
            continue
        for raiz, dirs, arquivos in os.walk(base):
            if _t.time() > limite:
                break
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
            for f in arquivos:
                if alvo in _norm_txt(f):
                    achados.append(Path(raiz) / f)
                    if len(achados) >= 10:
                        break
            if len(achados) >= 10:
                break
        if len(achados) >= 10:
            break
    if not achados:
        onde = pasta if pasta in pastas else "nas pastas do usuário"
        return f"Nenhum arquivo com '{nome}' em {onde}, senhor."
    linhas = [f"- {a}" for a in achados]
    return f"{len(achados)} arquivo(s) encontrado(s) com '{nome}':\n" + "\n".join(linhas)


# ==================== CONTROLE DE MÍDIA (v4.13.0) ====================

def _controlar_midia(acao: str) -> str:
    """Play/pause, próxima e anterior nas teclas de mídia do teclado —
    controla QUALQUER player que esteja tocando (Spotify, YouTube, WMP)."""
    import sys
    acao = acao or "play_pause"
    if acao not in ("play_pause", "proxima", "anterior"):
        return f"ação inválida '{acao}': use play_pause, proxima ou anterior."
    if sys.platform.startswith("win"):
        import ctypes
        vks = {"play_pause": 0xB3, "proxima": 0xB0, "anterior": 0xB1}
        vk = vks[acao]
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
        msgs = {"play_pause": "play/pause enviado, senhor",
                "proxima": "próxima faixa, senhor",
                "anterior": "faixa anterior, senhor"}
        return msgs[acao] + "."
    return ("o controle de mídia por tecla funciona no Windows, senhor — "
            "neste sistema eu ainda não consigo apertar as teclas de mídia.")
