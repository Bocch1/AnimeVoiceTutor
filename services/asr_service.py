"""Local Qwen3 Japanese speech recognition service with observable startup state."""

import asyncio
from io import BytesIO
import logging
import os
from threading import Lock

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, HTTPException, UploadFile

LOGGER = logging.getLogger("jvt.asr")
app = FastAPI(title="AnimeVoiceTutor Local ASR")
_model = None
_error = ""
_loading = False
_model_lock = Lock()
_infer_lock = Lock()
_warmup_task = None


def get_model():
    """Load the model only once, serializing concurrent requests and warmup."""
    global _model, _error, _loading
    with _model_lock:
        if _model is not None:
            return _model
        _loading = True
        _error = ""
        try:
            import torch
            from qwen_asr import Qwen3ASRModel

            path = os.environ.get("QWEN_ASR_MODEL", "").strip()
            if not path or not os.path.isfile(os.path.join(path, "config.json")):
                raise RuntimeError(f"Offline ASR model missing config.json: {path}")
            LOGGER.info("Loading Qwen3-ASR from %s", path)
            model = Qwen3ASRModel.from_pretrained(
                path,
                dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                max_inference_batch_size=1,
                max_new_tokens=256,
            )
            _model = model
            LOGGER.info("Qwen3-ASR loaded and ready")
            return _model
        except Exception as exc:
            _error = f"{type(exc).__name__}: {str(exc)[:320]}"
            LOGGER.exception("Qwen3-ASR initialization failed")
            raise
        finally:
            _loading = False


async def _warmup():
    try:
        await asyncio.to_thread(get_model)
    except Exception:
        # Keep the status endpoint available so the launcher can report the cause.
        pass


@app.on_event("startup")
async def startup():
    global _warmup_task
    _warmup_task = asyncio.create_task(_warmup())


@app.get("/health")
async def health():
    status = "ready" if _model is not None else ("loading" if _loading else ("error" if _error else "starting"))
    return {
        "ready": _model is not None,
        "status": status,
        "model": os.environ.get("QWEN_ASR_MODEL", "not configured"),
        "error": _error,
    }


def _recognize(content: bytes):
    samples, sample_rate = sf.read(BytesIO(content), dtype="float32")
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if not (sample_rate > 0 and sample_rate // 4 <= len(samples) <= sample_rate * 90):
        raise ValueError("Audio duration must be between 0.25 and 90 seconds")
    model = get_model()
    with _infer_lock:
        result = model.transcribe(audio=(np.asarray(samples), sample_rate), language="Japanese")
    if not result:
        raise RuntimeError("ASR returned no transcription")
    return {"text": result[0].text, "language": result[0].language}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    content = await audio.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file missing or too large")
    try:
        return await asyncio.to_thread(_recognize, content)
    except (ValueError, sf.LibsndfileError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)[:240]) from exc
    except Exception as exc:
        LOGGER.exception("ASR transcription failed")
        raise HTTPException(status_code=503, detail=f"Local ASR unavailable: {type(exc).__name__}: {str(exc)[:180]}") from exc
