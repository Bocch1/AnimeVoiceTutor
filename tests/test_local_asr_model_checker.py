"""Offline regression tests for model-directory validation."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_local_asr_model', ROOT / 'tools/check_local_asr_model.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_asr_config_only_is_not_complete(tmp_path):
    (tmp_path / 'config.json').write_text('{}')
    assert not m.complete(tmp_path)
    (tmp_path / 'model.safetensors').write_bytes(b'weights')
    assert m.complete(tmp_path)


def test_missing_index_shard_is_incomplete(tmp_path):
    (tmp_path / 'config.json').write_text('{}')
    (tmp_path / 'model.safetensors.index.json').write_text(json.dumps({'weight_map': {'a': 'one.safetensors','b':'two.safetensors'}}))
    (tmp_path / 'one.safetensors').write_bytes(b'x')
    assert not m.complete(tmp_path)
    (tmp_path / 'two.safetensors').write_bytes(b'y')
    assert m.complete(tmp_path)
