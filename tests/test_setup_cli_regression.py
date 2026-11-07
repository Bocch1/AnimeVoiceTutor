"""Regression tests for Windows source installation and post-install checks."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_windows_install_avoids_quote_sensitive_python_dash_c():
    installer = (ROOT / 'scripts/setup_source.ps1').read_text(encoding='utf-8')
    assert "Join-Path $PSScriptRoot 'runtime_import_probe.py'" in installer
    assert '& $pythonExe $probe --role $roleName' in installer
    assert '& $pythonExe -c' not in installer
    assert (ROOT / 'scripts/runtime_import_probe.py').is_file()


def test_runtime_probe_web_executable():
    probe = ROOT / 'scripts/runtime_import_probe.py'
    result = subprocess.run([sys.executable, str(probe), '--role', 'web'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'WEB_IMPORT_OK' in result.stdout


def test_asr_download_also_avoids_quote_sensitive_code():
    downloader = (ROOT / 'scripts/download_asr_model.ps1').read_text(encoding='utf-8')
    assert 'tools\\download_hf_model.py' in downloader
    assert '& $python -c' not in downloader
    assert (ROOT / 'tools/download_hf_model.py').is_file()


def test_source_verifier_allows_local_runtime_but_archive_rejects_it(tmp_path):
    verifier = _load('verify_public_source', 'scripts/verify_public_source.py')
    assert verifier.is_private_path('runtime/web/Scripts/python.exe')
    assert verifier.is_private_path('.avt-local.ps1')
    assert verifier.is_private_path('configs/frozen_tts_preset.json')
    assert not verifier.is_private_path('scripts/setup_source.ps1')
    archive = tmp_path / 'should_fail.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        for name in verifier.REQUIRED:
            zf.writestr(name, 'safe')
        zf.writestr('runtime/web/Scripts/python.exe', b'x')
    try:
        verifier.verify_archive(archive)
    except AssertionError as exc:
        assert 'runtime/web/Scripts/python.exe' in str(exc)
    else:
        raise AssertionError('Private runtime was accepted in an archive')
