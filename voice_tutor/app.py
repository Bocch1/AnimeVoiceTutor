"""Local Japanese conversation API: persistent text sessions and voice services."""

from functools import lru_cache
from pathlib import Path
import asyncio
import ipaddress
import json
import os
import secrets
import subprocess
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from .audio import MAX_UPLOAD_BYTES, synthesize, to_wav_16k_mono, transcribe
from .browser_presence import browser_presence
from .config import ROOT, Settings, load_voice_profiles
from .ports import web_port
from .conversation import LLMConversation, DeepSeekConversation
from .llm_config import LLMConfigStore, PROVIDER_URLS, choose_model
from .sessions import SessionStore
from .greetings import GREETING_BY_ID, GREETING_GROUPS
from . import characters

app = FastAPI(title="AnimeVoiceTutor", docs_url="/docs")
settings = Settings.from_env()
_exit_token = secrets.token_urlsafe(32)
llm_config = LLMConfigStore(defaults=settings)
voices = characters.current_voice_profiles()


@lru_cache(maxsize=1)
def session_store() -> SessionStore:
    return SessionStore(settings.store_path)


class BrowserClient(BaseModel):
    client_id: str = Field(min_length=8, max_length=100)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=80)
    correction_mode: str = Field(default="gentle", pattern="^(off|gentle|detailed)$")
    corrects_message_id: int | None = Field(default=None, ge=1)


class ProviderUpdate(BaseModel):
    provider: str = Field(pattern="^(deepseek|openai)$")
    model: str | None = Field(default=None, max_length=120)
    api_key: str = Field(default="", max_length=512)
    clear_key: bool = False


class PinRequest(BaseModel):
    pinned: bool


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    voice_id: str = Field(default="")
    session_id: str | None = Field(default=None, max_length=80)
    message_id: int | None = Field(default=None, ge=1)
    regenerate: bool = False


_greeting_locks: dict[str, asyncio.Lock] = {}
_title_worker: asyncio.Task | None = None

async def _finish_untitled_sessions():
    """Bounded, serialized backfill with no work when no LLM key is configured."""
    store=session_store()
    for _ in range(100):
        cfg=llm_config.runtime()
        if not cfg.api_key:
            return
        sid=store.claim_untitled()
        if not sid:
            return
        try:
            title=await LLMConversation(cfg).generate_title(store.history(sid, last_n=6))
            store.set_title(sid,title)
        except (httpx.HTTPError, RuntimeError, ValueError, KeyError):
            store.release_title_attempt(sid)
        await asyncio.sleep(1.0)

@app.get("/")
async def index():
    return FileResponse(ROOT / "web" / "index.html", media_type="text/html",
                        headers={"Cache-Control": "no-store, must-revalidate"})


# Character media is served only from validated installed packs, not the core.
@app.get('/api/characters')
async def characters_list():
    return {'active': characters.active_id(),
            'characters': [{'id': 'default', 'label': 'Standard Japanese',
                            'avatar': '日', 'voice_ready': False, 'has_portrait': False}]
                          + characters.list_installed()}


class CharacterSelection(BaseModel):
    id: str = Field(min_length=1, max_length=48)


@app.post('/api/characters/active')
async def set_character(req: CharacterSelection, request: Request):
    _same_origin(request)
    try:
        characters.select_character(req.id)
    except characters.PackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    voices.clear()
    voices.update(characters.current_voice_profiles())
    return {'active': characters.active_id(),
            'tts_restart_required': bool(voices)}


@app.get('/api/characters/active/content')
async def character_content():
    return characters.greetings_for_active()


@app.get('/api/characters/{identity}/{kind}')
async def character_media(identity: str, kind: str):
    if kind not in ('portrait', 'effects'):
        raise HTTPException(status_code=404, detail='Unknown character asset')
    try:
        path = characters.public_pack_asset(identity, kind)
    except characters.PackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    content_type = 'application/json' if kind == 'effects' else {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.webp': 'image/webp'}.get(path.suffix.lower(), 'application/octet-stream')
    return FileResponse(path, media_type=content_type,
                        headers={'Cache-Control': 'private, no-store',
                                 'X-Content-Type-Options': 'nosniff'})


@app.post('/api/characters/install')
async def character_import(request: Request, archive: UploadFile = File(...)):
    _same_origin(request, expected_content_type='multipart/form-data', require_browser_origin=True)
    from tempfile import NamedTemporaryFile
    total = 0
    try:
        with NamedTemporaryFile(prefix='avt_pack_', suffix='.zip', delete=False) as tmp:
            temp_path = Path(tmp.name)
            while chunk := await archive.read(1024 * 1024):
                total += len(chunk)
                if total > characters.MAX_ZIP_BYTES:
                    raise characters.PackError('Character ZIP exceeds size limit')
                tmp.write(chunk)
        installed = characters.import_pack(temp_path)
        # A successful UI installation immediately activates the imported pack.
        # The model is deliberately not treated as loaded until a managed TTS
        # listener has started with the selected weights.
        characters.select_character(installed['id'])
        voices.clear()
        voices.update(characters.current_voice_profiles())
        return {'installed': installed, 'active': characters.active_id(),
                'tts_restart_required': bool(voices)}
    except (characters.PackError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if 'temp_path' in locals():
            temp_path.unlink(missing_ok=True)


@app.post("/api/browser/ping")
async def browser_ping(req: BrowserClient):
    try:
        browser_presence.ping(req.client_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/browser/leave")
async def browser_leave(req: BrowserClient):
    try:
        browser_presence.leave(req.client_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@app.get("/api/browser/presence")
async def browser_status():
    return browser_presence.status()


def _require_local_exit_request(request: Request, *, post: bool = False) -> None:
    # Local-only system action: reject reverse proxies, DNS rebinding and cross-site calls.
    host = request.headers.get("host", "")
    origin_host = ""
    try:
        origin_host = urlparse("http://" + host).hostname or ""
        host_is_loopback = ipaddress.ip_address(origin_host).is_loopback
        peer_is_loopback = ipaddress.ip_address(request.client.host).is_loopback if request.client else False
    except ValueError:
        host_is_loopback = (origin_host == "localhost")
        try:
            peer_is_loopback = bool(request.client and ipaddress.ip_address(request.client.host).is_loopback)
        except ValueError:
            peer_is_loopback = False
    if not (host_is_loopback and peer_is_loopback):
        raise HTTPException(status_code=403, detail="Local access only")
    origin = request.headers.get("origin")
    if origin and origin != "http://" + host:
        raise HTTPException(status_code=403, detail="Same-origin request required")
    if post:
        if not origin or request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
            raise HTTPException(status_code=403, detail="Browser JSON request required")
        if not secrets.compare_digest(request.headers.get("x-avt-exit-token", ""), _exit_token):
            raise HTTPException(status_code=403, detail="Invalid exit token")


def _managed_run_id() -> str | None:
    # Never stop processes unless this very server belongs to the current managed run.
    state_path = ROOT / "data" / "app" / "local_services.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        run_id = state["run_id"]
        if not isinstance(run_id, str) or len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id.lower()):
            return None
        for proc in state.get("processes", []):
            if (proc.get("name") == "web" and proc.get("kind") == "listener"
                    and int(proc.get("pid", -1)) == os.getpid() and int(proc.get("port", -1)) == web_port()):
                return run_id
    except (OSError, TypeError, KeyError, ValueError):
        pass
    return None


@app.get("/api/system/exit-token")
async def exit_token(request: Request):
    _require_local_exit_request(request)
    available = _managed_run_id() is not None and (ROOT / "scripts" / "stop_app.ps1").is_file()
    return Response(content=json.dumps({"available": available, "token": _exit_token if available else None}),
                    media_type="application/json", headers={"Cache-Control": "no-store"})


async def _launch_managed_stop(run_id: str):
    # Dispatch only after the HTTP acknowledgement had time to reach the browser.
    await asyncio.sleep(0.65)
    script = ROOT / "scripts" / "stop_app.ps1"
    log_dir = ROOT / "data" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "web_exit.log").open("ab") as out:
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-RunId", run_id],
                cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0)
                               | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)),
            )
    except OSError:
        # The status file remains intact for the Stop AnimeVoiceTutor.cmd fallback.
        pass


@app.post("/api/system/exit")
async def exit_application(request: Request):
    _require_local_exit_request(request, post=True)
    run_id = _managed_run_id()
    if not run_id or not (ROOT / "scripts" / "stop_app.ps1").is_file():
        raise HTTPException(status_code=409, detail="Not running as a managed AnimeVoiceTutor session")
    asyncio.create_task(_launch_managed_stop(run_id))
    return {"ok": True, "status": "shutting_down"}


async def tcp_ready(url: str) -> bool:
    p = urlparse(url)
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(p.hostname, p.port or 80), timeout=0.5
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False


async def asr_health() -> tuple[bool, str]:
    """Report actual ASR model readiness, not just an open TCP port."""
    p = urlparse(settings.asr_url)
    target = f"{p.scheme}://{p.netloc}/health"
    try:
        async with httpx.AsyncClient(timeout=1.5, trust_env=False) as client:
            response = await client.get(target)
            response.raise_for_status()
            data = response.json()
        return bool(data.get("ready")), str(data.get("error") or data.get("status") or "")[:180]
    except (httpx.HTTPError, ValueError, KeyError):
        return False, "ASR service is not running"


@app.get("/api/status")
async def status():
    (asr, asr_detail), tts = await asyncio.gather(asr_health(), tcp_ready(settings.tts_url))
    active_llm = llm_config.public()
    active_character = characters.active_id()
    pack_voice_installed = bool(characters.current_voice_profiles())
    engine_root = Path(os.environ.get('AVT_TTS_ROOT') or (ROOT / 'external' / 'GPT-SoVITS-v5'))
    engine_present = (engine_root / 'api_v2.py').is_file()
    bound = bool(tts and characters.tts_binding_matches()) if settings.tts_enabled else False
    if active_character == 'default':
        tts_detail = '标准日语模式：未配置角色语音（可选）'
    elif not pack_voice_installed:
        tts_detail = '当前角色包没有语音模型；文字聊天仍可使用'
    elif not settings.tts_enabled:
        tts_detail = 'TTS_ENABLED 已关闭；角色模型尚未启用'
    elif bound:
        tts_detail = '当前角色模型已加载，语音服务可用'
    elif tts:
        tts_detail = '9880 端口已有 TTS 服务，但未验证为当前角色模型；请停止旧服务并重启测试版'
    elif not engine_present:
        tts_detail = '角色权重已安装；GPT-SoVITS 引擎源码尚未配置（Quick Setup 不包含引擎）'
    else:
        tts_detail = '角色权重已安装；TTS 未启动。请用 Start AnimeVoiceTutor.cmd 正常启动，不要使用 -TextOnly'
    return {
        "deepseek_configured": active_llm["configured"],
        "llm_configured": active_llm["configured"],
        "llm_provider": active_llm["provider"],
        "asr_ready": asr,
        "asr_detail": asr_detail,
        "tts_ready": bound,
        "tts_enabled": settings.tts_enabled,
        "tts_detail": tts_detail,
        "tts_pack_installed": pack_voice_installed,
        "tts_engine_available": engine_present,
        "tts_port_listening": bool(tts),
        "model": active_llm["model"],
        "voices": [{"id": p["id"], "label": p["label"],
                    "ready": bool(p["reference_audio_path"] and Path(p["reference_audio_path"]).is_file())}
                   for p in voices.values()],
        "character_id": active_character,
        "version": "0.12.0",
    }


def _same_origin(request: Request, *, expected_content_type: str = 'application/json', require_browser_origin: bool = False) -> None:
    # A malicious website should not be able to modify local API credentials.
    origin = request.headers.get("origin")
    host = request.headers.get("host", "")
    if origin:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != host:
            raise HTTPException(status_code=403, detail="API settings can only be changed from this local app")
    if require_browser_origin and not origin:
        # Referer is a valid fallback for local browser multipart uploads.
        referer = request.headers.get('referer', '')
        parsed = urlparse(referer)
        if parsed.scheme not in {'http', 'https'} or parsed.netloc != host:
            raise HTTPException(status_code=403, detail='Same-origin browser request required')
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != expected_content_type:
        raise HTTPException(status_code=415, detail=f'{expected_content_type} request required')


@app.get("/api/llm/config")
async def llm_get_config():
    return llm_config.public()


async def _discover_accessible_model(provider: str, api_key: str) -> str | None:
    """Ask the selected API which chat models are actually available to this key.

    Transient connectivity failures do not prevent a user from saving their key;
    the connection-test button checks the actual chat request separately.
    """
    url = PROVIDER_URLS[provider].rstrip("/") + "/models"
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        if response.status_code in (401, 403):
            raise HTTPException(status_code=400, detail="API Key 无效或没有访问权限")
        response.raise_for_status()
        data = response.json().get("data", [])
        available = [item.get("id") for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]
        model = choose_model(provider, available)
        if not model:
            raise HTTPException(status_code=400, detail="该 API Key 未提供应用支持的对话模型")
        return model


@app.post("/api/llm/config")
async def llm_update_config(req: ProviderUpdate, request: Request):
    _same_origin(request)
    model = req.model
    if req.api_key and model is None:
        try:
            model = await _discover_accessible_model(req.provider, req.api_key.strip())
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            # Allow offline configuration. A subsequent connection test will
            # distinguish connectivity problems from model-specific errors.
            model = None
    try:
        return llm_config.update(req.provider, model, req.api_key, req.clear_key)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/llm/test")
async def llm_test_connection(request: Request):
    _same_origin(request)
    runtime = llm_config.runtime()
    if not runtime.api_key:
        raise HTTPException(status_code=400, detail="API Key is not configured")
    body = {"model": runtime.model,
            "messages": [{"role": "user", "content": "Reply only with the Japanese word はい."}]}
    if runtime.provider == "deepseek":
        body.update({"max_tokens": 64, "thinking": {"type": "disabled"}})
    else:
        body["max_completion_tokens"] = 512
        if runtime.model.startswith(("gpt-6-luna", "gpt-6.1-terra", "gpt-6-sol")):
            body["reasoning_effort"] = "none"
    try:
        async with httpx.AsyncClient(timeout=min(runtime.timeout_seconds, 35.0)) as client:
            response = await client.post(runtime.base_url + "/chat/completions",
                                         json=body, headers={"Authorization": f"Bearer {runtime.api_key}"})
            response.raise_for_status()
            payload = response.json()
            if not payload.get("choices"):
                raise ValueError("Provider returned no choices")
    except (httpx.HTTPError, ValueError) as exc:
        # Do not disclose secrets, HTTP request headers or provider response bodies.
        code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        raise HTTPException(status_code=502, detail=(f"Provider returned HTTP {code}" if code else "Provider connection test failed")) from None
    return {"ok": True, "provider": runtime.provider, "model": runtime.model}


@app.get("/api/sessions")
async def sessions_list():
    global _title_worker
    # Kick off legacy title generation after returning the list; do not block chat.
    if _title_worker is None or _title_worker.done():
        if llm_config.runtime().api_key:
            _title_worker=asyncio.create_task(_finish_untitled_sessions())
    return {"sessions": session_store().list_sessions()}


@app.get("/api/sessions/{sid}")
async def session_get(sid: str):
    data = session_store().get(sid)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.patch("/api/sessions/{sid}/pin")
async def session_pin(sid: str, req: PinRequest, request: Request):
    _same_origin(request)
    if not session_store().set_pinned(sid, req.pinned):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "is_pinned": req.pinned}


@app.post("/api/sessions/{sid}/generate-title")
async def session_generate_title(sid: str, request: Request):
    _same_origin(request)
    store = session_store()
    session = store.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        title = await LLMConversation(llm_config.runtime()).generate_title(store.history(sid, last_n=6))
        title = store.set_title(sid, title)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not create conversation title: {str(exc)[:120]}") from None
    return {"ok": True, "title": title}


@app.delete("/api/sessions/{sid}")
async def session_delete(sid: str):
    if not session_store().delete(sid):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@app.post("/api/reset/{sid}")
async def session_reset(sid: str):
    session_store().delete(sid)
    return {"ok": True}


@app.get("/api/sessions/{sid}/export")
async def session_export(sid: str):
    try:
        payload = session_store().export_json(sid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    return Response(payload.encode("utf-8"), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="jvt_session_{sid}.json"'})


@app.post("/api/chat")
async def chat(req: ChatRequest):
    store = session_store()
    existing_id = req.session_id if req.session_id and store.get(req.session_id) else None
    revised_from = None
    if req.corrects_message_id is not None:
        if existing_id is None:
            raise HTTPException(status_code=400, detail="Revision requires an existing session")
        prior = store.message_in_session(existing_id, req.corrects_message_id)
        if prior is None:
            raise HTTPException(status_code=400, detail="Referenced user message not found in session")
        revised_from = prior["user_text"]
    try:
        agent = LLMConversation(llm_config.runtime())
        if revised_from is None:
            result = await agent.reply(store.history(existing_id), req.text.strip(), req.correction_mode)
        else:
            result = await agent.reply(store.history(existing_id), req.text.strip(),
                                       req.correction_mode, revised_from=revised_from)
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail=f"Conversation service failed: {str(exc)[:220]}") from exc
    sid, message_id = store.add_turn(existing_id, req.text.strip(), result, return_id=True,
                                     corrects_message_id=req.corrects_message_id)
    return {"session_id": sid, "message_id": message_id,
            "corrects_message_id": req.corrects_message_id, **result}


@app.post("/api/asr")
async def asr(audio: UploadFile = File(...)):
    content = await audio.read(MAX_UPLOAD_BYTES + 1)
    try:
        wav = to_wav_16k_mono(content)
        text = await transcribe(settings, wav)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"ASR service failed: {str(exc)[:220]}") from exc
    return {"text": text}


@app.get("/api/audio/{sid}/{message_id}")
async def replay_audio(sid: str, message_id: int, voice_id: str = ""):
    if not voice_id and voices:
        voice_id = next(iter(voices))
    """Play only existing WAV bytes. Never call the TTS engine for a replay."""
    store = session_store()
    if not store.message_in_session(sid, message_id) or voice_id not in voices:
        raise HTTPException(status_code=404, detail="Audio not found")
    try:
        path = store.audio_path(message_id, voice_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Audio not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio has not been generated")
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "private, no-store"})


@app.get("/api/greetings")
async def greetings_list():
    return {"groups": {key: [{"id": identity,"text":text} for identity,text in values]
                       for key,values in GREETING_GROUPS.items()}}


def _greeting_audio_path(identity: str) -> Path:
    from hashlib import sha256
    phrase_hash = sha256(GREETING_BY_ID[identity].encode("utf-8")).hexdigest()[:12]
    return settings.store_path.parent / "greeting_audio_cache" / f"{characters.active_id()}_{identity}_{phrase_hash}.wav"


@app.get("/api/greetings/{identity}/audio")
async def greeting_replay(identity: str):
    if identity not in GREETING_BY_ID:
        raise HTTPException(status_code=404,detail="Unknown greeting")
    path=_greeting_audio_path(identity)
    if not path.is_file():
        raise HTTPException(status_code=404,detail="Greeting audio not generated")
    return FileResponse(path,media_type="audio/wav",headers={"Cache-Control":"private, no-store"})


@app.post("/api/greetings/{identity}/speak")
async def greeting_speak(identity: str, request: Request):
    _same_origin(request)
    if identity not in GREETING_BY_ID:
        raise HTTPException(status_code=404,detail="Unknown greeting")
    path=_greeting_audio_path(identity)
    lock=_greeting_locks.setdefault(identity,asyncio.Lock())
    async with lock:
        if not path.is_file():
            profile=next(iter(voices.values()), None)
            if not profile:
                raise HTTPException(status_code=503,detail="No character voice configured")
            try:
                wav=await synthesize(settings,profile,GREETING_BY_ID[identity])
            except (httpx.HTTPError,RuntimeError,ValueError):
                raise HTTPException(status_code=502,detail="Welcome speech synthesis failed") from None
            path.parent.mkdir(parents=True,exist_ok=True)
            import os
            from uuid import uuid4
            temp=path.with_name(path.name+"."+uuid4().hex+".tmp")
            try:
                temp.write_bytes(wav)
                os.replace(temp,path)
            finally:
                temp.unlink(missing_ok=True)
    return FileResponse(path,media_type="audio/wav",headers={"Cache-Control":"private, no-store"})


@app.get('/api/secret-greetings')
async def local_secret_greetings():
    """Hidden greetings belong to the selected pack, never the neutral core."""
    return {'greetings': characters.greetings_for_active()['hidden_greetings']}


@app.get('/api/characters/{identity}/greeting-audio/{greeting_id}')
async def packaged_greeting_audio(identity: str, greeting_id: str):
    """Play bundled WAVs without invoking a TTS engine."""
    if identity != characters.active_id():
        raise HTTPException(status_code=404, detail='Character is not active')
    folder, manifest = characters.active_manifest()
    if not folder or not manifest:
        raise HTTPException(status_code=404, detail='Character is not installed')
    entries = [entry for group in manifest.get('greetings', {}).values() for entry in group]
    entries += manifest.get('hidden_greetings', [])
    match = next((entry for entry in entries if entry.get('id') == greeting_id), None)
    if not match or not match.get('audio'):
        raise HTTPException(status_code=404, detail='No recorded greeting')
    try:
        path = characters._local_file(folder, match['audio'])
    except characters.PackError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type='audio/wav', headers={'Cache-Control': 'private, no-store'})


# v0.9.18: robust persisted audio for user-editable hidden greetings.
# Cache identity is derived from the user-supplied ID, exact speech text, and voice.
class SecretGreetingSpeakRequest(BaseModel):
    identity: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=600)
    voice_id: str = Field(default="", max_length=96)


_secret_greeting_locks: dict[str, asyncio.Lock] = {}


@app.post("/api/secret-greetings/speak")
async def secret_greeting_speak(req: SecretGreetingSpeakRequest, request: Request):
    """Generate once, then replay the same WAV across browser and app restarts."""
    from hashlib import sha256

    _same_origin(request)
    # The ID is always hashed, never used as a path. User-authored IDs can contain Japanese text.
    profile = voices.get(req.voice_id)
    if not characters.tts_binding_matches():
        raise HTTPException(status_code=503, detail="Selected character model is not loaded; restart the managed TTS service")
    if profile is None:
        raise HTTPException(status_code=404, detail="Unknown voice ID")

    # The digest prevents path traversal and invalidates stale WAVs after text edits.
    digest = sha256(
        (req.identity + "\x00" + req.voice_id + "\x00" + req.text).encode("utf-8")
    ).hexdigest()
    destination = settings.store_path.parent / "greeting_audio_cache" / f"secret_{digest}.wav"
    lock = _secret_greeting_locks.setdefault(digest, asyncio.Lock())
    async with lock:
        if destination.is_file() and destination.stat().st_size > 44:
            return FileResponse(
                destination, media_type="audio/wav",
                headers={"Cache-Control": "private, no-store", "X-AVT-Audio-Cache": "HIT"},
            )
        try:
            wav = await synthesize(settings, profile, req.text)
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"TTS service failed: {str(exc)[:220]}") from exc
        if not wav or len(wav) <= 44:
            raise HTTPException(status_code=502, detail="TTS returned no usable WAV audio")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name("." + digest + "." + secrets.token_hex(6) + ".tmp")
        try:
            temp.write_bytes(wav)
            os.replace(temp, destination)
        finally:
            temp.unlink(missing_ok=True)
    return FileResponse(
        destination, media_type="audio/wav",
        headers={"Cache-Control": "private, no-store", "X-AVT-Audio-Cache": "GENERATED"},
    )


@app.post("/api/speak")
async def speak(req: SpeakRequest):
    if not characters.tts_binding_matches():
        raise HTTPException(status_code=503, detail='Selected character model is not loaded; restart the managed TTS service')
    profile = voices.get(req.voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Unknown voice ID")
    store = session_store()
    is_session_message = req.session_id is not None or req.message_id is not None
    path = None
    if is_session_message:
        if req.session_id is None or req.message_id is None:
            raise HTTPException(status_code=400, detail="Both session_id and message_id are required")
        msg = store.message_in_session(req.session_id, req.message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found")
        if msg["reply_ja"] != req.text:
            raise HTTPException(status_code=409, detail="Text differs from the saved assistant reply")
        path = store.audio_path(req.message_id, req.voice_id)
        if path.is_file() and not req.regenerate:
            return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "private, no-store"})
    try:
        wav = await synthesize(settings, profile, req.text)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"TTS service failed: {str(exc)[:220]}") from exc
    if is_session_message:
        store.save_audio(req.session_id, req.message_id, req.voice_id, wav)
    return Response(content=wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})
