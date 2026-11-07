"""Offline regressions for two import paths and managed TTS model refresh."""
from pathlib import Path
import json
import os
import subprocess
import sys
import zipfile

import pytest
from fastapi.testclient import TestClient

from tools import install_and_select_character as installer
from voice_tutor import app as module, characters

ROOT = Path(__file__).resolve().parents[1]


def _archive(tmp_path, *, text='おはようございます。'):
    path=tmp_path/'voice.zip'
    payload={'schema_version':1,'id':'example_voice','display_name':'Example Voice',
             'greetings':{'morning':[{'id':'hello_1','text':text}]},'hidden_greetings':[]}
    with zipfile.ZipFile(path,'w') as output:
        output.writestr('character.json',json.dumps(payload,ensure_ascii=False))
    return path


def test_first_run_uses_same_python_as_doctor_and_refreshes_after_import():
    tasks=(ROOT/'scripts/first_run_tasks.ps1').read_text(encoding='utf-8-sig')
    resolver=(ROOT/'scripts/resolve_runtime_python.ps1').read_text()
    assert "-Role web | Select-Object -Last 1" in tasks
    assert "refresh_after_character_install.ps1" in tasks
    assert tasks.count("refresh_after_character_install.ps1") == 2
    assert "Join-Path $root '.venv\\Scripts\\python.exe'" in resolver
    assert 'WEB_RUNTIME_MISSING' in tasks
    assert 'runtime\\web\\Scripts\\python.exe' not in tasks


def test_already_installed_zip_identical_is_safe_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(characters,'PACK_ROOT',tmp_path/'packs')
    monkeypatch.setattr(characters,'SELECTION',tmp_path/'app'/'selected_character.json')
    path=_archive(tmp_path)
    assert installer.install_once(path)['id']=='example_voice'
    assert installer.install_once(path)['id']=='example_voice'
    characters.select_character('example_voice')
    assert characters.active_id()=='example_voice'
    assert characters.archive_matches_installed(path,'example_voice')
    different=_archive(tmp_path,text='違う音声です。')
    assert not characters.archive_matches_installed(different,'example_voice')
    with pytest.raises(characters.PackError,match='different files'):
        installer.install_once(different)
    assert characters.validate_manifest(characters.PACK_ROOT/'example_voice')['greetings']['morning'][0]['text']=='おはようございます。'


def test_repeated_archive_rejects_unsafe_filename_even_if_contents_match(tmp_path,monkeypatch):
    monkeypatch.setattr(characters,'PACK_ROOT',tmp_path/'packs')
    archive=_archive(tmp_path)
    installer.install_once(archive)
    weird=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(weird,'w') as dst:
        with zipfile.ZipFile(archive,'r') as src:
            dst.writestr('character.json',src.read('character.json'))
        entry=zipfile.ZipInfo('assets\\unexpected.png')
        entry.filename='assets\\unexpected.png'
        dst.writestr(entry,b'junk')
    assert not characters.archive_matches_installed(weird,'example_voice')


def test_web_install_and_select_schedule_only_managed_voice(monkeypatch,tmp_path):
    monkeypatch.setattr(characters,'PACK_ROOT',tmp_path/'packs')
    monkeypatch.setattr(characters,'SELECTION',tmp_path/'app'/'selected_character.json')
    monkeypatch.setattr(characters,'BINDING',tmp_path/'app'/'tts_model_binding.json')
    monkeypatch.setattr(module,'voices',{})
    called=[]
    monkeypatch.setattr(module,'_schedule_managed_character_refresh',lambda:called.append(True) or True)
    archive=_archive(tmp_path)
    with TestClient(module.app) as client, archive.open('rb') as f:
        response=client.post('/api/characters/install',headers={'Origin':'http://testserver'},
                             files={'archive':('voice.zip',f,'application/zip')})
        assert response.status_code==200
        assert response.json()['tts_refresh_scheduled'] is True
        response=client.post('/api/characters/active',headers={'Origin':'http://testserver'},json={'id':'example_voice'})
        assert response.status_code==200
        assert response.json()['tts_refresh_scheduled'] is True
    assert len(called)==2


def test_refresh_ps_refuses_unowned_tts_and_does_not_reset_web():
    refresh=(ROOT/'scripts/refresh_character_tts.ps1').read_text(encoding='utf-8')
    assert "TTS_FOREIGN_LISTENER_ON_9880" in refresh
    assert "TTS_RELOAD_RUN_CHANGED" in refresh
    assert "TTS_RELOAD_SELECTION_CHANGED" in refresh
    assert "Trusted-Tts" in refresh
    assert "Stop-Process -Id $oldPid" in refresh
    assert "Get-CimInstance Win32_Process" in refresh
    assert "tts_model_binding.json" in refresh
    assert "TTS_MODEL_REFRESH_READY" in refresh
    assert "TTS_MODEL_REFRESH_FAILED" in refresh
    assert "stop_app.ps1" not in refresh
    assert 'taskkill' not in refresh.lower()
    assert "run_id" in refresh


def test_frontend_distinguishes_character_assets_from_generated_speech():
    html=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert 'waitForManagedCharacterVoice(' in html
    assert 'tts_refresh_scheduled' in html
    assert "status.tts_refresh?.status==='failed'" in html
    assert '正在加载角色语音' in html


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows PowerShell 5.1 only')
def test_windows_powershell_refresh_scripts_parse():
    scripts = [ROOT / 'scripts/refresh_character_tts.ps1',
               ROOT / 'scripts/refresh_after_character_install.ps1',
               ROOT / 'scripts/first_run_tasks.ps1']
    # PowerShell -Command does not reliably expose trailing process arguments
    # as $args[0]. Pass the absolute script path through the child environment.
    command = (
        '$path=$env:AVT_PS_PARSE_TARGET;'
        'if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { exit 2 };'
        '$t=$null;$e=$null;'
        '[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$t,[ref]$e)|Out-Null;'
        'if ($e.Count -gt 0) { $e | ForEach-Object { Write-Output $_.Message }; exit 1 }'
    )
    for script in scripts:
        env = os.environ.copy()
        env['AVT_PS_PARSE_TARGET'] = str(script.resolve())
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
            env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, (script.name, result.stdout, result.stderr)
