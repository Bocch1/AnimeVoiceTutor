"""The browser controls the lifecycle of one-click managed services."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voice_tutor import app as module
from voice_tutor.browser_presence import BrowserPresence

ROOT = Path(__file__).resolve().parents[1]


def test_browser_presence_tracks_multiple_tabs(monkeypatch):
    state = BrowserPresence()
    monkeypatch.setattr(module, "browser_presence", state)
    with TestClient(module.app) as client:
        assert client.get('/api/browser/presence').json()['ever_connected'] is False
        assert client.post('/api/browser/ping', json={'client_id':'avt_aaaaaaaaaa'}).status_code == 200
        assert client.post('/api/browser/ping', json={'client_id':'avt_bbbbbbbbbb'}).status_code == 200
        assert client.get('/api/browser/presence').json()['active_clients'] == 2
        assert client.post('/api/browser/leave', json={'client_id':'avt_aaaaaaaaaa'}).status_code == 200
        assert client.get('/api/browser/presence').json()['active_clients'] == 1
        assert client.post('/api/browser/leave', json={'client_id':'avt_bbbbbbbbbb'}).status_code == 200
        last = client.get('/api/browser/presence').json()
        assert last['active_clients'] == 0
        assert last['ever_connected'] is True
        assert last['inactive_seconds'] >= 0
        assert client.post('/api/browser/ping', json={'client_id':'x'}).status_code == 422
        assert client.post('/api/browser/ping', json={'client_id':'invalid!id'}).status_code == 400


def test_browser_expiry_and_reconnect(monkeypatch):
    from voice_tutor import browser_presence as presence_module
    clock = {'now': 100.0}
    monkeypatch.setattr(presence_module, 'monotonic', lambda: clock['now'])
    state = BrowserPresence(expiry_seconds=30)
    state.ping('avt_first_tab')
    clock['now'] = 135.0
    assert state.status()['active_clients'] == 0
    assert state.status()['inactive_seconds'] == 0
    clock['now'] = 141.0
    assert state.status()['inactive_seconds'] == 6.0
    state.ping('avt_first_tab')
    assert state.status()['inactive_seconds'] is None
    assert state.status()['active_clients'] == 1


def test_one_click_scripts_record_actual_listeners_and_watch_browser():
    launcher = (ROOT / 'scripts/launch_app.ps1').read_text(encoding='utf-8')
    stopper = (ROOT / 'scripts/stop_app.ps1').read_text(encoding='utf-8')
    watcher = (ROOT / 'scripts/monitor_browser.ps1').read_text(encoding='utf-8')
    html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
    assert 'Record-Listener' in launcher
    assert 'Get-NetTCPConnection' in launcher
    assert 'run_id=' in launcher
    assert 'monitor_browser.ps1' in launcher
    assert 'api/browser/presence' in watcher
    assert 'active_clients' in watcher
    assert 'stop_app.ps1' in watcher
    assert 'RunId' in watcher and 'RunId' in stopper
    assert 'Trusted-Listener' in stopper
    assert '/api/browser/ping' in html
    assert '/api/browser/leave' in html
    assert 'sendBeacon' in html
    assert 'pageshow' in html
