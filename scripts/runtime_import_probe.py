"""Verify Python dependencies for a single AnimeVoiceTutor runtime.

Run as a script rather than with python -c so Windows PowerShell 5.1 cannot
remove Python string quotes while constructing a native-process command line.
"""
from __future__ import annotations

import argparse
import importlib
import sys

ROLE_PACKAGES = {
    "web": ("fastapi", "uvicorn", "httpx", "pydantic"),
    "asr": ("torch", "qwen_asr", "fastapi", "uvicorn"),
    "tts": ("torch", "yaml", "soundfile"),
}


def check_runtime(role: str) -> None:
    for package in ROLE_PACKAGES[role]:
        importlib.import_module(package)

    if role in {"asr", "tts"}:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError(f"{role.upper()} requires a CUDA-enabled PyTorch runtime and a compatible NVIDIA driver")
        print(f"{role.upper()}_CUDA_DEVICE: {torch.cuda.get_device_name(0)}")

    print(f"{role.upper()}_IMPORT_OK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=sorted(ROLE_PACKAGES), required=True)
    args = parser.parse_args()
    try:
        check_runtime(args.role)
    except (ImportError, RuntimeError) as exc:
        print(f"{args.role.upper()}_RUNTIME_CHECK_FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
