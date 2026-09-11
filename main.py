import asyncio
import re
import threading
import json
import logging
import sys
import traceback
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)

from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )


# ── Limpeza de transcrição ─────────────────────────────────────────────────
_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:
    """Remove artefatos <ctrlXX> e caracteres de controle da transcrição do Gemini."""
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()


# ── Tool declarations ──────────────────────────────────────────────────────────
from tools_manifest import TOOL_DECLARATIONS
from core.settings import SETTINGS
from version import __version__

log = logging.getLogger("jarvis")


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None

        # Registry de tools: adicionar tool nova = 1 linha no _build_tool_handlers
        self.tool_handlers = self._build_tool_handlers()
        self._tool_timeout = SETTINGS.get("tool_timeout_seconds", 90)

        # Consistência: alguma tool declarada ao Gemini sem handler?
        declared = {t["name"] for t in TOOL_DECLARATIONS}
        specials = {"save_memory", "screen_process", "agent_task", "shutdown_jarvis"}
        missing  = declared - specials - set(self.tool_handlers)
        if missing:
            log.warning(f"Tools declaradas sem handler: {sorted(missing)}")

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        lang = SETTINGS.get("language", "")
        lang_ctx = (
            f"[LANGUAGE]\n"
            f"The user's preferred language is {lang}. "
            f"Always reply in that language unless the user switches.\n\n"
        ) if lang else ""

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        if lang_ctx:
            parts.append(lang_ctx)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=SETTINGS.get("voice", "Charon")
                    )
                )
            ),
        )

    def _check_updates_once(self):
        """Consulta o manifesto de update em background e avisa se houver novidade."""
        try:
            from updater import check_update
            manifest = check_update()
            if manifest:
                self.ui.write_log(f"SYS: Nova versão {manifest['latest_version']} disponível.")
                self.speak(f"Sir, version {manifest['latest_version']} is now available.")
        except Exception as e:
            log.warning(f"Updater: {e}")

    def _build_tool_handlers(self):
        """Registry de tools — adicionar tool nova = 1 linha aqui."""
        ui = self.ui
        return {
            "open_app":          lambda a: open_app(parameters=a, response=None, player=ui),
            "weather_report":    lambda a: weather_action(parameters=a, player=ui),
            "browser_control":   lambda a: browser_control(parameters=a, player=ui),
            "file_controller":   lambda a: file_controller(parameters=a, player=ui),
            "send_message":      lambda a: send_message(parameters=a, response=None, player=ui, session_memory=None),
            "reminder":          lambda a: reminder(parameters=a, response=None, player=ui),
            "youtube_video":     lambda a: youtube_video(parameters=a, response=None, player=ui),
            "computer_settings": lambda a: computer_settings(parameters=a, response=None, player=ui),
            "desktop_control":   lambda a: desktop_control(parameters=a, player=ui),
            "code_helper":       lambda a: code_helper(parameters=a, player=ui, speak=self.speak),
            "dev_agent":         lambda a: dev_agent(parameters=a, player=ui, speak=self.speak),
            "web_search":        lambda a: web_search_action(parameters=a, player=ui),
            "computer_control":  lambda a: computer_control(parameters=a, player=ui),
            "game_updater":      lambda a: game_updater(parameters=a, player=ui, speak=self.speak),
            "flight_finder":     lambda a: flight_finder(parameters=a, player=ui),
        }

    async def _run_tool(self, fn, timeout=90):
        """Executa a tool em thread separada com timeout.

        Impede que uma tool travada (ex.: site que não responde)
        bloqueie o loop de áudio para sempre.
        """
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, fn), timeout=timeout
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        log.info(f"🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        # ── save_memory: caminho rápido e silencioso ────────────────────────
        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                log.info(f"💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        result = "Done."

        try:
            if name == "screen_process":
                # módulo de visão fala direto com o usuário — não esperamos
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "shutdown_jarvis":
                log.info("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")

                def _shutdown():
                    import time, os
                    time.sleep(1)
                    os._exit(0)
                threading.Thread(target=_shutdown, daemon=True).start()

            else:
                handler = self.tool_handlers.get(name)
                if handler is None:
                    result = f"Unknown tool: {name}"
                    log.warning(f"Tool sem handler registrado: {name}")
                else:
                    r = await self._run_tool(lambda: handler(args), timeout=self._tool_timeout)
                    result = r or "Done."

        except asyncio.TimeoutError:
            result = f"Tool '{name}' timed out after {self._tool_timeout}s."
            self.speak_error(name, "the operation timed out")

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        log.info(f"📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        log.info("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_running_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                data = indata.tobytes()

                def _put():
                    # Buffer cheio -> descarta o chunk (evita QueueFull)
                    if not self.out_queue.full():
                        self.out_queue.put_nowait(
                            {"data": data, "mime_type": "audio/pcm"}
                        )

                loop.call_soon_threadsafe(_put)

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                log.info("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            log.info(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        log.info("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                            out_buf = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            log.info(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            log.info(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        log.info("[JARVIS] 🔊 Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue

                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)

        except Exception as e:
            log.info(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        delay = 3  # backoff: 3s -> 6s -> 12s -> 24s -> 30s (teto)
        while True:
            try:
                log.info("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=SETTINGS["model"], config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_running_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)
                    self._turn_done_event = asyncio.Event()

                    log.info("[JARVIS] ✅ Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS online.")
                    delay = 3  # conectou: reseta o backoff
                    threading.Thread(target=self._check_updates_once, daemon=True).start()

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                log.info(f"[JARVIS] ⚠️ {e}")
                traceback.print_exc()
                err = str(e).lower()
                if "api key" in err or "401" in err or "permission" in err or "unauthenticated" in err:
                    self.ui.write_log("SYS: API key inválida — verifique config/api_keys.json")
                    delay = 60

            self.set_speaking(False)
            self.ui.set_state("THINKING")
            log.info(f"[JARVIS] 🔄 Reconnecting in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, SETTINGS.get("max_reconnect_delay_seconds", 30))


def main():
    from core.logger import setup_logging
    setup_logging(BASE_DIR)
    log.info(f"JARVIS v{__version__} iniciando...")

    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            log.info("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()