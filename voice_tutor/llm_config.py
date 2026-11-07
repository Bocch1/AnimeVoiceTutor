"""Mutable, user-local provider settings. API secrets never travel to the UI after saving.

Windows uses per-user DPAPI encryption; on other OSes the on-disk file is
owner-only (0600). The server must remain bound to localhost.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading

from .config import ROOT, Settings

PROVIDER_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
}
DEFAULT_MODELS = {"deepseek": "deepseek-flash", "openai": "gpt-6-luna"}
# Highest-priority chat-compatible models for a conversational, latency-sensitive app.
# Model IDs are discovered from each provider's authenticated /models endpoint.
PREFERRED_MODELS = {
    "deepseek": ("deepseek-flash", "deepseek-v4-pro"),
    "openai": ("gpt-6-luna", "gpt-6.1-terra", "gpt-6.1-sol", "gpt-6-sol", "gpt-4.1-mini", "gpt-4o-mini"),
}


def choose_model(provider: str, available: list[str]) -> str | None:
    if provider not in PREFERRED_MODELS:
        return None
    offered = set(available)
    return next((model for model in PREFERRED_MODELS[provider] if model in offered), None)

MODEL_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/+-]{0,119}$")


def _dpapi(data: bytes, *, protect: bool) -> bytes:
    """Protect Windows secrets for the current logon account (no external deps)."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    def blob(payload):
        buffer = (ctypes.c_byte * len(payload)).from_buffer_copy(payload)
        return DATA_BLOB(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer

    source, memory = blob(data)
    output = DATA_BLOB()
    api = ctypes.WinDLL("crypt32", use_last_error=True)
    method = api.CryptProtectData if protect else api.CryptUnprotectData
    method.argtypes = ([ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR,
                        ctypes.POINTER(DATA_BLOB), wintypes.LPVOID,
                        wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
                       if protect else
                       [ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
                        ctypes.POINTER(DATA_BLOB), wintypes.LPVOID,
                        wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)])
    method.restype = wintypes.BOOL
    flags = 0x1  # CRYPTPROTECT_UI_FORBIDDEN
    if not method(ctypes.byref(source), None, None, None, None, flags, ctypes.byref(output)):
        raise OSError(ctypes.get_last_error(), "Windows DPAPI operation failed")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(output.pbData, ctypes.c_void_p))


def _encode_key(key: str) -> str:
    if sys.platform == "win32":
        return "dpapi:" + base64.b64encode(_dpapi(key.encode("utf-8"), protect=True)).decode("ascii")
    return "plain:" + base64.b64encode(key.encode("utf-8")).decode("ascii")


def _decode_key(encoded: str) -> str:
    if not encoded:
        return ""
    prefix, marker, value = encoded.partition(":")
    if not marker or prefix not in {"dpapi", "plain"}:
        raise ValueError("Unsupported stored key format")
    data = base64.b64decode(value, validate=True)
    if prefix == "dpapi":
        if sys.platform != "win32":
            raise ValueError("Windows DPAPI key cannot be opened on this platform")
        data = _dpapi(data, protect=False)
    return data.decode("utf-8")


@dataclass(frozen=True)
class LLMRuntime:
    provider: str
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float


class LLMConfigStore:
    def __init__(self, path: Path | None = None, defaults: Settings | None = None):
        self.path = Path(path or ROOT / "data" / "app" / "llm_config.json")
        self.defaults = defaults or Settings.from_env()
        self.lock = threading.RLock()
        self._settings = {"active": "deepseek", "providers": {}}
        if self.path.exists():
            config = json.loads(self.path.read_text(encoding="utf-8"))
            if config.get("active") in PROVIDER_URLS and isinstance(config.get("providers"), dict):
                self._settings = config

    def _entry(self, provider: str) -> dict:
        entry = self._settings.get("providers", {}).get(provider, {})
        return entry if isinstance(entry, dict) else {}

    def _key(self, provider: str) -> str:
        entry = self._entry(provider)
        if "secret" in entry:
            return _decode_key(entry["secret"])
        if entry.get("removed"):
            return ""
        if provider == "deepseek":
            return self.defaults.api_key
        return os.getenv("OPENAI_API_KEY", "").strip()

    def _model(self, provider: str) -> str:
        candidate = self._entry(provider).get("model")
        if isinstance(candidate, str) and MODEL_ID.fullmatch(candidate):
            return candidate
        if provider == "deepseek":
            fallback = self.defaults.model
        else:
            fallback = os.getenv("OPENAI_MODEL", DEFAULT_MODELS["openai"])
        return fallback if MODEL_ID.fullmatch(fallback) else DEFAULT_MODELS[provider]

    def runtime(self) -> LLMRuntime:
        with self.lock:
            provider = self._settings["active"]
            return LLMRuntime(provider=provider, api_key=self._key(provider),
                              model=self._model(provider), base_url=PROVIDER_URLS[provider],
                              timeout_seconds=self.defaults.timeout_seconds)

    @staticmethod
    def _masked_hint(key: str) -> str:
        # Show only the final four characters; never treat this as an editable key.
        return ("••••••••" + key[-4:]) if len(key) >= 8 else ("••••••••" if key else "")

    def public(self) -> dict:
        with self.lock:
            active = self._settings["active"]
            return {"provider": active, "model": self._model(active),
                    "configured": bool(self._key(active)),
                    "providers": {p: {"model": self._model(p), "has_api_key": bool(self._key(p)),
                                      "key_hint": self._masked_hint(self._key(p))}
                                  for p in PROVIDER_URLS}}

    def update(self, provider: str, model: str | None = None, api_key: str = "", clear_key: bool = False) -> dict:
        if provider not in PROVIDER_URLS:
            raise ValueError("Unsupported API provider")
        if model is not None:
            model = model.strip()
            if not MODEL_ID.fullmatch(model) or "://" in model:
                raise ValueError("Invalid model identifier")
        if len(api_key) > 512 or any(ch in api_key for ch in "\r\n"):
            raise ValueError("Invalid API key")
        if api_key and clear_key:
            raise ValueError("Cannot set and remove an API key together")
        with self.lock:
            entries = {k: dict(v) for k, v in self._settings.get("providers", {}).items() if isinstance(v, dict)}
            entry = entries.get(provider, {})
            if model is not None:
                entry["model"] = model
            elif api_key or "model" not in entry:
                # Replacing a credential resets a possibly stale model ID.
                entry["model"] = DEFAULT_MODELS[provider]
            if api_key:
                entry["secret"] = _encode_key(api_key.strip())
                entry.pop("removed", None)
            elif clear_key:
                entry.pop("secret", None)
                entry["removed"] = True
            entries[provider] = entry
            updated = {"active": provider, "providers": entries}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic replacement, owner-only permissions on POSIX.
            fd, temp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".llm_config_", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(updated, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.chmod(temp, 0o600)
                except OSError:
                    pass
                os.replace(temp, self.path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            self._settings = updated
            return self.public()
