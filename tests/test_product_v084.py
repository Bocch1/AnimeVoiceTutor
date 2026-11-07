"""Regression tests for synchronous text+voice and forced TTS regeneration."""
from pathlib import Path
from fastapi.testclient import TestClient
from voice_tutor import app as module
from voice_tutor.sessions import SessionStore


def test_regeneration_bypasses_cache_and_replay_remains_cache_only(tmp_path, monkeypatch):
    store = SessionStore(tmp_path / 'history.sqlite3')
    monkeypatch.setattr(module, 'session_store', lambda: store)
    monkeypatch.setattr(module, 'voices', {'azusa_e36': {'id': 'azusa_e36'}})
    sid, mid = store.add_turn(None, 'こんにちは', {
        'reply_ja': '今日はいい天気ですね。', 'correction_ja': '', 'feedback_zh': ''
    }, return_id=True)
    generated = []

    async def fake_synthesize(_settings, _voice, _text):
        generated.append(len(generated) + 1)
        return b'RIFF' + bytes([generated[-1]]) * 16 + b'WAVE'

    monkeypatch.setattr(module, 'synthesize', fake_synthesize)
    monkeypatch.setattr(module.characters, 'tts_binding_matches', lambda: True)
    request = {'text': '今日はいい天気ですね。', 'voice_id': 'azusa_e36',
               'session_id': sid, 'message_id': mid}
    with TestClient(module.app) as client:
        old = client.post('/api/speak', json=request)
        assert old.status_code == 200
        assert len(generated) == 1
        assert client.post('/api/speak', json=request).content == old.content
        assert len(generated) == 1
        assert client.get(f'/api/audio/{sid}/{mid}').content == old.content
        assert len(generated) == 1
        new = client.post('/api/speak', json={**request, 'regenerate': True})
        assert new.status_code == 200 and new.content != old.content
        assert len(generated) == 2
        replay = client.get(f'/api/audio/{sid}/{mid}')
        assert replay.content == new.content
        assert 'no-store' in replay.headers['cache-control']
        assert len(generated) == 2
        assert client.post('/api/speak', json=request).content == new.content
        assert client.get(f'/api/audio/wrong/{mid}').status_code == 404


def test_regeneration_failure_does_not_destroy_last_audio(tmp_path, monkeypatch):
    store = SessionStore(tmp_path / 'history.sqlite3')
    monkeypatch.setattr(module, 'session_store', lambda: store)
    monkeypatch.setattr(module, 'voices', {'azusa_e36': {'id': 'azusa_e36'}})
    sid, mid = store.add_turn(None, 'こんにちは', {
        'reply_ja': '元気です。', 'correction_ja': '', 'feedback_zh': ''
    }, return_id=True)
    old = b'RIFF0000WAVE'
    store.save_audio(sid, mid, 'azusa_e36', old)

    async def broken(_settings, _voice, _text):
        raise RuntimeError('model temporarily unavailable')

    monkeypatch.setattr(module, 'synthesize', broken)
    monkeypatch.setattr(module.characters, 'tts_binding_matches', lambda: True)
    payload = {'text': '元気です。', 'voice_id': 'azusa_e36',
               'session_id': sid, 'message_id': mid, 'regenerate': True}
    with TestClient(module.app) as client:
        assert client.post('/api/speak', json=payload).status_code == 502
        assert client.get(f'/api/audio/{sid}/{mid}').content == old


def test_main_ui_removes_old_copy_labels_and_explanations():
    html = (Path(__file__).parents[1] / 'web' / 'index.html').read_text(encoding='utf-8')
    for hidden_label in [
        '想聊什么就说什么。', '日语对话，自然练习', '本地保存文字与生成语音；',
        '麦克风待命', '无需选择场景', 'id="topNew"', 'id="recordStatus"'
    ]:
        assert hidden_label not in html
    assert "regenerate," in html
    assert "$('text').value = '';" in html
    assert '正在合成语音' not in html or 'pending' in html
    assert '音频' not in html or '/api/audio/' in html
