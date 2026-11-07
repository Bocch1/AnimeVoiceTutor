"""Exercise a running extracted AnimeVoiceTutor copy via real local HTTP endpoints.

No models or environments are downloaded or modified. A successful voice test
requires an actual local TTS synthesis followed by an actual ASR transcription.
"""

import argparse
from io import BytesIO
from pathlib import Path
import sys

import httpx
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice_tutor.ports import web_port

BASE = f"http://127.0.0.1:{web_port()}"


def check_wav(payload: bytes) -> tuple[float, float]:
    """Validate audible WAV samples, not merely an HTTP success code."""
    with sf.SoundFile(BytesIO(payload)) as stream:
        if stream.format != "WAV":
            raise RuntimeError("TTS did not return WAV audio")
        duration = stream.frames / stream.samplerate
        audio = stream.read(dtype="float32", always_2d=True)
    if not 0.3 <= duration <= 30.0:
        raise RuntimeError(f"Unexpected TTS WAV duration: {duration:.2f}s")
    if not np.isfinite(audio).all():
        raise RuntimeError("TTS WAV contains non-finite samples")
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= 0.001:
        raise RuntimeError("TTS WAV is effectively silent")
    return duration, peak


def run(voice: bool, tts_only: bool, asr_only: bool, save_wav: Path) -> None:
    with httpx.Client(timeout=240.0, trust_env=False) as client:
        response = client.get(BASE + "/")
        response.raise_for_status()
        if "AnimeVoiceTutor" not in response.text:
            raise RuntimeError("Unexpected WebUI response")
        status_response = client.get(BASE + "/api/status")
        status_response.raise_for_status()
        status = status_response.json()
        if status.get("version") != "0.12.0":
            raise RuntimeError("Unexpected app version; another instance may be serving the configured Web port (expected 0.12.0)")
        print("PASS: WebUI and /api/status respond (AnimeVoiceTutor source v0.12.0)")
        print("INFO: LLM configured:", bool(status.get("llm_configured")))
        if not voice and not tts_only and not asr_only:
            print("Web smoke test complete. Run with --voice for actual ASR and TTS inference.")
            return

        if not asr_only:
            if not status.get("tts_ready"):
                raise RuntimeError("TTS is not ready according to /api/status")
            profiles = [p for p in status.get("voices", []) if p.get("id") and p.get("ready")]
            if not profiles:
                raise RuntimeError("No configured TTS voice with a readable reference audio file")
            profile = profiles[0]
            print("INFO: Testing voice profile:", profile["id"])
            response = client.post(BASE + "/api/speak", json={"text": "おはようございます。今日は日本語を練習しましょう。", "voice_id": profile["id"]})
            response.raise_for_status()
            wav = response.content
            duration, peak = check_wav(wav)
            save_wav.parent.mkdir(parents=True, exist_ok=True)
            save_wav.write_bytes(wav)
            print(f"PASS: TTS generated audible WAV ({duration:.2f}s; peak {peak:.3f}); saved to {save_wav}")
        else:
            wav = None

        if not tts_only:
            if not status.get("asr_ready"):
                raise RuntimeError("ASR is not ready according to /api/status: " + str(status.get("asr_detail")))
            if wav is None:
                if not save_wav.is_file():
                    raise RuntimeError("ASR-only mode requires a local WAV file at --save-wav")
                wav = save_wav.read_bytes()
                check_wav(wav)
            response = client.post(BASE + "/api/asr", files={"audio": ("smoke.wav", wav, "audio/wav")})
            response.raise_for_status()
            transcript = response.json().get("text", "").strip()
            if not transcript:
                raise RuntimeError("ASR returned no Japanese transcription")
            print("PASS: ASR transcribed generated local audio:", transcript)
        print("PASS: Requested live smoke checks completed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    exclusive = parser.add_mutually_exclusive_group()
    exclusive.add_argument("--voice", action="store_true", help="Test WebUI, TTS synthesis, and ASR transcription")
    exclusive.add_argument("--tts-only", action="store_true", help="Test WebUI and real TTS synthesis")
    exclusive.add_argument("--asr-only", action="store_true", help="Test ASR on previously generated WAV")
    parser.add_argument("--save-wav", type=Path, default=Path("data/smoke_tests/tts_smoke.wav"))
    args = parser.parse_args()
    try:
        run(args.voice, args.tts_only, args.asr_only, args.save_wav)
        return 0
    except (httpx.HTTPError, ValueError, RuntimeError, OSError, sf.LibsndfileError) as exc:
        print("FAIL:", str(exc)[:500], file=sys.stderr)
        print("Start the extracted source using Start AnimeVoiceTutor.cmd -NoBrowser; inspect data/logs if needed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
