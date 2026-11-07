"""Dependency-only Qwen3-ASR preflight; does not import or download the model."""
from __future__ import annotations
import importlib.util
import json
import sys

REQUIRED = ("qwen_asr", "torch", "numpy", "soundfile", "fastapi", "uvicorn")


def check():
    missing = []
    for name in REQUIRED:
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except Exception as exc:
            missing.append(f"{name} (probe error: {type(exc).__name__})")
    try:
        multipart = any(
            importlib.util.find_spec(name) is not None
            for name in ("multipart", "python_multipart")
        )
    except Exception:
        multipart = False
    if not multipart:
        missing.append("python-multipart")
    result = {
        "python": sys.executable,
        "version": sys.version.split()[0],
        "missing": missing,
        "status": "ready" if not missing else "dependencies_missing",
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0 if not missing else 10


if __name__ == "__main__":
    raise SystemExit(check())
