"""Ensure the runtime can reuse an existing Conda ASR installation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_asr_resolver_preserves_named_conda_environments():
    resolver = (ROOT / 'scripts/resolve_runtime_python.ps1').read_text(encoding='utf-8-sig')
    launcher = (ROOT / 'scripts/start_asr_local.ps1').read_text(encoding='utf-8-sig')
    assert 'jvt-asr' in resolver
    assert 'jvt-qwen-asr' in resolver
    assert 'CONDA_PREFIX' in resolver
    assert 'AVT_ASR_PYTHON' in resolver
    assert 'Test-ASRPython $resolved' in launcher
