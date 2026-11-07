"""Three-language two-stage installer contract tests (offline)."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_complete_core_entrypoint_and_multilingual_gui():
    launcher = (ROOT / 'First Run Setup.cmd').read_text(encoding='utf-8')
    gui = (ROOT / 'scripts/first_run_gui.ps1').read_text(encoding='utf-8-sig')
    assert '-STA' in launcher and 'first_run_gui.ps1' in launcher
    assert 'patch payload' in launcher
    assert 'System.Windows.Forms' in gui
    assert 'Start-Transcript' in gui
    assert '-RedirectStandardOutput' not in gui
    assert '-RedirectStandardError' not in gui
    assert 'Incomplete Core directory' in gui
    for key in ('zh-CN', 'en', 'ja'):
        assert f"$script:translations['{key}']" in gui
    for text in ('简体中文', 'English', '日本語',
                 '安装基础语音环境', 'Install voice base', '音声環境をインストール',
                 '自动下载已固定版本', 'Import and activate', '取り込んで有効化'):
        assert text in gui
    assert "'1.7B'" in gui and '$model.SelectedIndex=0' in gui
    assert "-DownloadPretrained" in gui and "Launch-Job" in gui


def test_two_stage_pinned_source_and_safety_checks():
    text = (ROOT / 'scripts/first_run_tasks.ps1').read_text(encoding='utf-8-sig')
    assert "ValidateSet('base','character','character_release','list_characters','diagnostics','voice_test','capture')" in text
    assert 'quick_setup.ps1' in text and '-Mode full' in text
    assert 'download_asr_model.ps1' in text
    assert 'RVC-Boss/GPT-SoVITS.git' not in text  # read URL from manifest
    assert 'fetch_pinned_engine.py' in text
    assert 'MANAGED_ENGINE_VERSION_UNVERIFIED' in text
    assert 'ENGINE_REVISION_MISMATCH' in text
    assert 'VOICE_SMOKE_TEST_FAILED' in text
    assert 'INCOMPLETE_SOURCE_DIRECTORY' in text
    assert 'STEP_1_BASE_SETUP_COMPLETE' in text
    assert 'STEP_2_CHARACTER_IMPORT_COMPLETE' in text
    assert 'WEB_RUNTIME_MISSING' in text
    assert 'EXISTING_ENGINE_UNCHANGED' in text
    assert 'ENGINE_OVERLAY_APPLIED_WITH_BACKUP' in text
    assert 'STEP_2_CHARACTER_IMPORT_COMPLETE' in text
    assert 'CHARACTER_RELEASE_INSTALL_FAILED' in text
    assert 'Get-FileHash' in (ROOT / 'scripts/first_run_preflight.ps1').read_text()


def test_baseline_lock_sha256_matches_and_scope():
    data = json.loads((ROOT / 'release/install_specs/voice_baseline.json').read_text())
    assert data['platform'] == 'windows-x64'
    assert data['asr_model']['repo'] == 'Qwen/Qwen3-ASR-1.7B'
    assert data['tts_engine']['reference'] == '04a44eb977586645f33594b72af13a035a2056c6'
    assert data['tts_engine']['developer_base_commit_confirmed'] is True
    assert data['tts_engine']['developer_worktree_modified'] is True
    assert not data['tts_engine']['same_as_developer_verified_engine']
    for name in ('web', 'asr', 'tts'):
        lock = ROOT / 'release' / 'install_specs' / (name + '_requirements.lock')
        assert hashlib.sha256(lock.read_bytes()).hexdigest() == data['runtime_lock_sha256'][name]
    assert data['pretrained_japanese']['expected_sha256'] is None


def test_release_manifest_and_no_private_model_files():
    paths = (ROOT / 'release/public_source_files.txt').read_text().splitlines()
    paths = [x for x in paths if x.strip() and not x.startswith('#')]
    for name in ('First Run Setup.cmd','scripts/first_run_gui.ps1','scripts/first_run_tasks.ps1',
                 'scripts/first_run_preflight.ps1','scripts/capture_voice_baseline.ps1',
                 'tools/install_and_select_character.py', 'tools/install_tts_pretrained.py',
                 'release/install_specs/voice_baseline.json', 'tests/test_first_run_setup_v013.py',
                 'tools/github_character_release.py','tools/fetch_pinned_engine.py','tools/apply_engine_overlay.py'):
        assert name in paths
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths))
    assert not any(item.startswith(('data/','external/','runtime/','models/')) for item in paths)
    assert not any(item.lower().endswith(('.pth','.ckpt','.wav')) for item in paths)


def test_character_installer_cli_and_selection(monkeypatch, tmp_path):
    from tools import install_and_select_character as module
    import sys as platform_sys
    installed, selected = [], []
    monkeypatch.setattr(module,'import_pack',lambda path: installed.append(path) or {'id':'sample_voice'})
    monkeypatch.setattr(module,'select_character',selected.append)
    zip_path = tmp_path / 'voice.zip'
    monkeypatch.setattr(platform_sys,'argv',['tool.py',str(zip_path),'--select'])
    module.main()
    assert installed == [zip_path.resolve()]
    assert selected == ['sample_voice']
    result=subprocess.run([sys.executable,str(ROOT/'tools/install_and_select_character.py'),'--help'],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode == 0 and '--select' in result.stdout


def test_local_snapshot_records_runtime_and_character_hashes():
    text = (ROOT/'scripts/capture_voice_baseline.ps1').read_text(encoding='utf-8')
    for name in ('engine_commit','tts_python_version','torch_version','tts_pip_freeze_sha256',
                 'nvidia_driver','ffmpeg_version','character_file_sha256','models/sovits.pth'):
        assert name in text
    assert 'data\\app\\voice_baseline_local.json' in text
    for field in ('engine_worktree_dirty', 'engine_git_status', 'GPT_SoVITS/TTS_infer_pack/TTS.py', 'GPT_SoVITS/configs/tts_infer.yaml'):
        assert field in text
