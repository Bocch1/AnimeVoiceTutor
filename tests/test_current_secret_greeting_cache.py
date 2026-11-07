"""Local, mocked cache checks: no API keys, GPU, network or character voice needed."""
from types import SimpleNamespace

from fastapi.testclient import TestClient
from voice_tutor import app as module


def test_secret_audio_persists_and_changes_with_text(tmp_path, monkeypatch):
    calls = []

    async def fake_synthesize(settings, profile, text):
        calls.append(text)
        return b'RIFF' + b'\x00' * 80

    monkeypatch.setattr(module, 'settings', SimpleNamespace(store_path=tmp_path / 'sessions.sqlite3'))
    monkeypatch.setattr(module, 'voices', {'azusa_e36': {'id': 'azusa_e36'}})
    monkeypatch.setattr(module, 'synthesize', fake_synthesize)
    monkeypatch.setattr(module.characters, 'tts_binding_matches', lambda: True)
    module._secret_greeting_locks.clear()
    headers = {'Origin': 'http://testserver'}
    with TestClient(module.app) as client:
        payload = {'identity': 'regression_hello', 'text': 'こんにちは。', 'voice_id': 'azusa_e36'}
        first = client.post('/api/secret-greetings/speak', json=payload, headers=headers)
        second = client.post('/api/secret-greetings/speak', json=payload, headers=headers)
        assert first.status_code == second.status_code == 200
        assert first.content == second.content
        assert first.headers['x-avt-audio-cache'] == 'GENERATED'
        assert second.headers['x-avt-audio-cache'] == 'HIT'
        assert calls == ['こんにちは。']
        changed = client.post('/api/secret-greetings/speak', json={**payload, 'text': 'こんばんは。'}, headers=headers)
        assert changed.status_code == 200
        assert changed.headers['x-avt-audio-cache'] == 'GENERATED'
        assert calls == ['こんにちは。', 'こんばんは。']
        blocked = client.post('/api/secret-greetings/speak', json=payload, headers={'Origin': 'https://evil.example'})
        assert blocked.status_code == 403
    cache_dir = tmp_path / 'greeting_audio_cache'
    assert len(list(cache_dir.glob('secret_*.wav'))) == 2
