"""Validate the public first-run tooling without installing any external models."""
from pathlib import Path
import importlib.util
from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]


def test_source_launchers_and_runtime_reuse_are_present():
    for path in (
        'advanced/Use Existing Models.cmd', 'advanced/Download ASR Model.cmd', 'advanced/Doctor AnimeVoiceTutor.cmd', 'advanced/Verify Source.cmd',
        'scripts/verify_source_tests.ps1',
        'advanced/Test AnimeVoiceTutor.cmd', 'scripts/bootstrap_uv.ps1',
        'scripts/load_local_runtime.ps1', 'scripts/reuse_existing_installation.ps1',
        'scripts/download_asr_model.ps1', 'scripts/doctor_source.ps1',
        'scripts/test_source.ps1', 'tools/smoke_voice_services.py',
    ):
        assert (ROOT / path).is_file(), path
    assert '.avt-local.ps1' in (ROOT / '.gitignore').read_text(encoding='utf-8')


def test_external_voice_root_is_supported():
    assert 'AVT_TTS_ROOT' in (ROOT / 'scripts/start_tts_api_frozen.ps1').read_text(encoding='utf-8')
    assert 'AVT_TTS_ROOT' in (ROOT / 'scripts/start_source.ps1').read_text(encoding='utf-8')
    assert 'JVT_ASR_MODEL_PATH' in (ROOT / 'scripts/start_asr_local.ps1').read_text(encoding='utf-8')


def _module():
    spec = importlib.util.spec_from_file_location('smoke_voice_services', ROOT / 'tools/smoke_voice_services.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wav_validation_with_synthetic_wave():
    module = _module()
    t = np.arange(16000, dtype=np.float32) / 16000
    x = (np.sin(2 * np.pi * 440 * t) * 0.15).astype(np.float32)
    out = BytesIO()
    sf.write(out, x, 16000, format='WAV', subtype='PCM_16')
    duration, peak = module.check_wav(out.getvalue())
    assert 0.99 < duration < 1.01 and 0.14 < peak < 0.16
    with pytest.raises((RuntimeError, sf.LibsndfileError)):
        module.check_wav(b'not a wav')
