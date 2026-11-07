"""Optional quick setup must remain separate from custom/manual installation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_quick_setup_is_optional_and_role_aware():
    launcher = (ROOT / 'advanced/Quick Setup.cmd').read_text(encoding='utf-8')
    script = (ROOT / 'scripts/quick_setup.ps1').read_text(encoding='utf-8')
    assert 'scripts\\quick_setup.ps1' in launcher
    assert "[ValidateSet('menu', 'full', 'web', 'asr', 'tts', 'help')]" in script
    assert "'all'" in script and "'setup_source.ps1'" in script
    assert 'DryRun' in script and 'DRY_RUN_OK' in script
    assert 'advanced\\Download ASR Model.cmd' in script
    assert 'download_asr_model.ps1' not in script
    assert 'start_source.ps1' not in script


def test_manual_setup_and_existing_installer_are_preserved():
    manual = (ROOT / 'docs/INSTALLATION.md').read_text(encoding='utf-8')
    assert 'pip install -e' in manual
    assert 'uv pip sync' in manual
    assert 'AVT_TTS_PYTHON' in manual
    assert 'AVT_ASR_PYTHON' in manual
    assert 'model' in manual.lower()
    assert (ROOT / 'advanced/Setup AnimeVoiceTutor.cmd').is_file()
    assert (ROOT / 'scripts/setup_source.ps1').is_file()


def test_quick_setup_is_published_by_allowlist():
    manifest = (ROOT / 'release/public_source_files.txt').read_text(encoding='utf-8').splitlines()
    for name in ('advanced/Quick Setup.cmd', 'scripts/quick_setup.ps1', 'docs/INSTALLATION.md', 'tests/test_quick_setup_contract.py'):
        assert name in manifest
    assert 'models/' not in manifest
