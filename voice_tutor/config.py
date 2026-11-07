"""Configuration for the local conversation app and its model services."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def localhost_url(value: str) -> str:
    """Disallow unexpected remote audio services and SSRF via configuration."""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("ASR/TTS endpoints must be bound to localhost")
    return value


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    base_url: str
    asr_url: str
    tts_url: str
    tts_enabled: bool
    timeout_seconds: float
    store_path: Path
    correction_mode: str
    tts_retries: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            asr_url=localhost_url(os.getenv("ASR_URL", "http://127.0.0.1:8766/transcribe")),
            tts_url=localhost_url(os.getenv("TTS_URL", "http://127.0.0.1:9880/tts")),
            tts_enabled=os.getenv("TTS_ENABLED", "true").lower() in {"true", "1", "yes"},
            timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "180")),
            store_path=(ROOT / os.getenv("SESSION_DB_PATH", "data/app/conversations.sqlite3")).resolve(),
            correction_mode=os.getenv("CORRECTION_MODE", "gentle"),
            tts_retries=max(1, min(3, int(os.getenv("TTS_MAX_ATTEMPTS", "3")))),
        )


def load_voice_profiles() -> dict:
    """Load voice references; no model weights are distributed in this package."""
    path = ROOT / "configs" / "voice_profiles_v08.json"
    if not path.exists():
        path = ROOT / "configs" / "voices.json"
    if not path.exists():
        path = ROOT / "configs" / "voice_profiles_v08.example.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    profiles = {}
    for profile in raw["voices"]:
        record = dict(profile)
        ref = record.get("reference_audio_path", "")
        if ref and not Path(ref).is_absolute():
            ref = str((ROOT / ref).resolve())
        record["reference_audio_path"] = ref
        profiles[record["id"]] = record
    return profiles
