"""Regression: Web launched with a virtual environment owns its TTS and Exit actions."""
import asyncio
import json
import os
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from voice_tutor import app as module

ROOT = Path(__file__).resolve().parents[1]


def request(run_id: str) -> Request:
    return Request({
        'type': 'http', 'method': 'GET', 'path': '/api/system/managed-identity',
        'headers': [(b'host', b'127.0.0.1:8767'), (b'x-avt-run-id', run_id.encode('ascii'))],
        'client': ('127.0.0.1', 23456), 'server': ('127.0.0.1', 8767),
        'scheme': 'http', 'query_string': b'',
    })


def test_web_managed_by_run_id_even_when_windows_pid_registration_is_late(tmp_path, monkeypatch):
    run = 'abcdef0123456789abcdef0123456789'
    state = tmp_path/'data'/'app'/'local_services.json'
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({'run_id': run, 'web_port': 8767,
                                 'processes': [{'name': 'web', 'pid': 99999,
                                                'script': 'scripts/start_web.ps1'}]}))
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'web_port', lambda: 8767)
    monkeypatch.setenv('AVT_MANAGED_RUN_ID', run)
    assert module._managed_run_id() == run
    info = asyncio.run(module.managed_identity(request(run)))
    assert info == {'pid': os.getpid(), 'web_port': 8767, 'managed': True}
    with pytest.raises(HTTPException) as exception:
        asyncio.run(module.managed_identity(request('1'*32)))
    assert exception.value.status_code == 403


def test_unmanaged_web_rejected_even_if_same_port_or_wrapper_recorded(tmp_path, monkeypatch):
    run = 'abc123de'*4
    file = tmp_path/'data'/'app'/'local_services.json'
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps({'run_id': run, 'web_port': 8767,
                                'processes': [{'name': 'web', 'pid': 88888,
                                               'script': 'scripts/start_web.ps1'}]}))
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'web_port', lambda: 8767)
    monkeypatch.delenv('AVT_MANAGED_RUN_ID', raising=False)
    assert module._managed_run_id() is None
    with pytest.raises(HTTPException) as exception:
        asyncio.run(module.managed_identity(request(run)))
    assert exception.value.status_code == 403
    monkeypatch.setenv('AVT_MANAGED_RUN_ID', run)
    monkeypatch.setattr(module, 'web_port', lambda: 8777)
    assert module._managed_run_id() is None


def test_launcher_uses_authenticated_web_claim_and_fail_closed_check():
    text = (ROOT/'scripts/launch_app.ps1').read_text(encoding='utf-8-sig')
    assert '$env:AVT_MANAGED_RUN_ID = $script:runId' in text
    assert "'X-AVT-Run-Id'=$runId" in text
    assert 'api/system/managed-identity' in text
    assert 'WEB_MANAGED_IDENTITY_MISSING' in text
    assert 'Record-Listener \'web\' $webPort' in text
    assert 'Get-NetTCPConnection' in text
    assert 'Get-ManagedWebListener $webPort $previousRun' in text
    assert "Write-Host \"Recovering a verified local AnimeVoiceTutor" not in text


def test_status_and_interface_distinguish_missing_management_from_missing_weights():
    app_source=(ROOT/'voice_tutor/app.py').read_text(encoding='utf-8')
    ui=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert '"managed_session": bool(managed_run)' in app_source
    assert '当前网页没有受管启动登记' in app_source
    assert '新窗口可以直接使用退出按钮' in ui
    assert '不再' not in ui[ui.index('if(!info.available||!info.token)'):ui.index('if(!info.available||!info.token)')+150]


def test_retry_voice_endpoint_requires_managed_session(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(module, '_require_local_exit_request', lambda request: None)
    monkeypatch.setattr(module, '_same_origin', lambda request, **kwargs: None)
    monkeypatch.setattr(module.characters, 'active_id', lambda: 'example_voice')
    monkeypatch.setattr(module.characters, 'current_voice_profiles', lambda: {'example': {}})
    monkeypatch.setattr(module, '_managed_run_id', lambda: None)
    with TestClient(module.app) as client:
        result=client.post('/api/characters/refresh-tts', json={}, headers={'Origin':'http://testserver'})
    assert result.status_code == 409
    assert '受管' in result.json()['detail']


def test_retry_voice_endpoint_only_queues_reload_for_verified_managed_run(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(module, '_require_local_exit_request', lambda request: None)
    monkeypatch.setattr(module, '_same_origin', lambda request, **kwargs: None)
    monkeypatch.setattr(module.characters, 'active_id', lambda: 'example_voice')
    monkeypatch.setattr(module.characters, 'current_voice_profiles', lambda: {'example': {}})
    monkeypatch.setattr(module, '_managed_run_id', lambda: 'a'*32)
    called=[]
    monkeypatch.setattr(module, '_schedule_managed_character_refresh', lambda: called.append(True) or True)
    with TestClient(module.app) as client:
        result=client.post('/api/characters/refresh-tts', json={}, headers={'Origin':'http://testserver'})
    assert result.status_code == 200
    assert result.json()['tts_refresh_scheduled'] is True
    assert called == [True]


def test_web_has_click_to_retry_voice_and_visible_error_detail():
    ui=(ROOT/'web/index.html').read_text(encoding='utf-8')
    assert 'id="retryTtsBtn"' in ui
    assert 'id="ttsStatusDetail"' in ui
    assert "'/api/characters/refresh-tts'" in ui
    assert "$('retryTtsBtn').onclick = retryCharacterTts" in ui
