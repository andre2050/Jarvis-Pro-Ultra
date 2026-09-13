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

from . import memory

# ---------- callback opcional (o app registra para avisar quando o timer dispara) ----------
on_timer_fire = None


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
    ]


# ==================== EXECUÇÃO ====================

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
