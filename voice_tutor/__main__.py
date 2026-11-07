"""CLI for the local-first AnimeVoiceTutor app."""
import argparse
import importlib.util
import shutil
import subprocess
from .config import Settings
from . import characters
from .ports import web_port


def doctor():
    s=Settings.from_env()
    print("AnimeVoiceTutor v0.12.0 environment check")
    print("DeepSeek configured:", bool(s.api_key))
    print("FFmpeg found:", bool(shutil.which("ffmpeg")))
    print("ASR URL:", s.asr_url)
    print("TTS URL:", s.tts_url)
    print("TTS enabled:", s.tts_enabled)
    print("Voice profiles:", [(v["id"], v.get("reference_audio_path")) for v in characters.current_voice_profiles().values()])
    if shutil.which("nvidia-smi"):
        proc=subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                            capture_output=True, text=True, timeout=10, check=False)
        print("GPU:", proc.stdout.strip())


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("command", choices=["doctor", "serve"])
    args=ap.parse_args()
    if args.command == "doctor":
        doctor()
    else:
        import uvicorn
        uvicorn.run("voice_tutor.app:app", host="127.0.0.1", port=web_port(), reload=False, workers=1)


if __name__ == "__main__":
    main()
