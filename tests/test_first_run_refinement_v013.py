"""Regression contracts for desktop first-run voice setup refinement."""
from pathlib import Path
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[1]


def test_version_check_uses_local_project_version_not_012():
    data=(ROOT/'tools/smoke_voice_services.py').read_text(encoding='utf-8')
    assert 'local_version =' in data and 'status.get("version") != local_version' in data
    assert 'expected 0.12.0' not in data


def test_first_run_diagnosis_is_strict_separate_and_no_service_required():
    gui=(ROOT/'scripts/first_run_gui.ps1').read_text(encoding='utf-8-sig')
    task=(ROOT/'scripts/first_run_tasks.ps1').read_text(encoding='utf-8-sig')
    diagnose=(ROOT/'scripts/diagnose_voice_base.ps1').read_text(encoding='utf-8-sig')
    assert "Add-Button 'install'" in gui and "Add-Button 'doctor'" in gui and "Add-Button 'advanced'" in gui
    assert "$advancedForm.Controls.Add($control)" in gui and "@($capture,$test)" in gui
    assert 'diagnose_voice_base.ps1' in task
    assert 'VOICE_BASE_INCOMPLETE' in task
    assert 'VOICE_BASE_DIAGNOSTICS_PASS' in diagnose
    assert 'runtime_import_probe.py' in diagnose
    assert 'check_local_asr_model.py' in diagnose
    assert 'FFmpeg' in diagnose and 'pretrained_models' in diagnose
    assert "'ok' = '操作成功。'" in gui


def test_color_avatar_and_localized_character_composer():
    ui=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert '#sidebar #roleAvatar img,.role-portrait-thumb img' in ui
    assert 'filter:none!important' in ui
    assert 'function updateComposerPlaceholder()' in ui
    assert '`发消息给${label}`' in ui
    assert '`Message ${label}`' in ui
    assert '`${label}にメッセージを送る`' in ui
    assert "'开始对话'" in ui
    assert "if(typeof updateComposerPlaceholder==='function')updateComposerPlaceholder();" in ui


def test_initializing_status_does_not_instruct_text_only_restart():
    app=(ROOT/'voice_tutor/app.py').read_text(encoding='utf-8')
    html=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert 'tts_initializing' in app and 'tts_initializing' in html
    assert '不要使用 -TextOnly' not in app


def test_original_color_avatar_is_separate_from_monochrome_portrait(tmp_path, monkeypatch):
    import json
    from voice_tutor import characters
    from pathlib import Path
    monkeypatch.setattr(characters, 'PACK_ROOT', tmp_path)
    folder=tmp_path/'sample';(folder/'assets').mkdir(parents=True)
    (folder/'assets'/'subject.png').write_bytes(b'greyscale')
    (folder/'assets'/'avatar_color.png').write_bytes(b'color')
    (folder/'character.json').write_text(json.dumps({
        'schema_version':1,'id':'sample','display_name':'Sample',
        'portrait':'assets/subject.png','avatar_color':'assets/avatar_color.png',
        'greetings':{},'hidden_greetings':[]
    }),encoding='utf-8')
    assert characters.validate_manifest(folder)['avatar_color']=='assets/avatar_color.png'
    assert characters.public_pack_asset('sample','avatar')==(folder/'assets'/'avatar_color.png')
    assert characters.public_pack_asset('sample','portrait')==(folder/'assets'/'subject.png')
    assert characters.list_installed()[0]['has_color_avatar']
    ui=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert "'/avatar'" in ui
