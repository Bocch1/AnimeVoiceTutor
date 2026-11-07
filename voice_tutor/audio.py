"""Local audio ingestion, Qwen ASR and frozen GPT-SoVITS inference adapter."""

from io import BytesIO
import json
import logging
import math
import re
import secrets
import subprocess
from urllib.parse import urlparse
from .config import ROOT

import httpx
import numpy as np
import soundfile as sf

LOGGER = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


def to_wav_16k_mono(data: bytes) -> bytes:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Audio is empty or exceeds the 12 MB limit")
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
               "-t", "90", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "wav", "pipe:1"]
    try:
        proc = subprocess.run(command, input=data, capture_output=True, timeout=30, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is not installed or not on PATH") from exc
    if proc.returncode != 0 or not proc.stdout:
        raise ValueError("Audio conversion failed; check recording format")
    return proc.stdout


def validate_wav_bytes(data: bytes) -> None:
    with sf.SoundFile(BytesIO(data)) as wav:
        if wav.frames < wav.samplerate // 4:
            raise ValueError("Recording is too short")
        if wav.frames / wav.samplerate > 90:
            raise ValueError("Recording exceeds 90 seconds")


async def transcribe(settings, wav_bytes: bytes) -> str:
    validate_wav_bytes(wav_bytes)
    async with httpx.AsyncClient(timeout=settings.timeout_seconds, trust_env=False) as client:
        response = await client.post(settings.asr_url,
                                     files={"audio": ("recording.wav", wav_bytes, "audio/wav")})
        response.raise_for_status()
        return str(response.json().get("text", "")).strip()


def clean_tts_text(text: str) -> str:
    """Remove ellipses known to truncate this model; preserve other spoken text."""
    text = re.sub(r"…+|\.{3,}", "", text)
    return text.strip()


def wav_valid(data: bytes, source_length: int) -> tuple[bool, str]:
    """Reject empty/unreasonably long WAVs, without using arbitrary stop distances."""
    try:
        with sf.SoundFile(BytesIO(data)) as sound:
            duration = sound.frames / sound.samplerate
            if duration < 0.24 or duration > max(24.0, source_length * 0.6):
                return False, f"Unreasonable duration {duration:.2f}s"
            audio = sound.read(dtype="float32", always_2d=False)
        x = np.asarray(audio)
        if x.ndim == 2:
            x = x.mean(axis=1)
        if x.size == 0 or not np.isfinite(x).all():
            return False, "Invalid audio samples"
        peak = float(np.max(np.abs(x)))
        if peak < 0.001:
            return False, "Audio is almost silent"
        return True, "ok"
    except (ValueError, RuntimeError, sf.LibsndfileError) as exc:
        return False, str(exc)


def frozen_tts_request(profile: dict, text: str, seed: int) -> dict:
    """Use the central, frozen FP32 E36 v5turbo profile without ad-hoc defaults."""
    from .characters import active_preset
    active = active_preset()
    if not active:
        raise RuntimeError("No voice model is installed for the active character")
    config = active["preset"]
    request = dict(config["inference"])
    request.update({
        "text": clean_tts_text(text),
        "ref_audio_path": profile["reference_audio_path"],
        "prompt_text": profile["prompt_text"],
        "seed": seed,
    })
    return request


async def synthesize(settings, profile: dict, text: str) -> bytes:
    if not settings.tts_enabled:
        raise RuntimeError("TTS_ENABLED is false")
    reference = profile.get("reference_audio_path", "")
    if not reference:
        raise RuntimeError("Voice reference is not configured")
    cleaned = clean_tts_text(text)
    if not cleaned:
        raise ValueError("Empty TTS text")
    if len(cleaned) > 600:
        raise ValueError("TTS text exceeds 600 characters")
    endpoint = profile.get("tts_url") or settings.tts_url
    if urlparse(endpoint).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("TTS endpoint must be localhost")
    last_error = "unknown error"
    async with httpx.AsyncClient(timeout=settings.timeout_seconds, trust_env=False) as client:
        for attempt in range(settings.tts_retries):
            seed = secrets.randbelow(2**32 - 1)
            request = frozen_tts_request(profile, cleaned, seed)
            try:
                response = await client.post(endpoint, json=request)
                response.raise_for_status()
                ok, reason = wav_valid(response.content, len(cleaned))
                if ok:
                    return response.content
                last_error = reason
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)[:240]
            LOGGER.warning("JVT TTS attempt %s/%s rejected: %s", attempt + 1, settings.tts_retries, last_error)
    raise RuntimeError(f"TTS failed after {settings.tts_retries} attempts: {last_error}")
