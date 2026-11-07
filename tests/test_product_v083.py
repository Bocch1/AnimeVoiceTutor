"""Product integration: no scenarios, persistent generated audio, and replay-only endpoint."""
from io import BytesIO
from pathlib import Path
import asyncio
import json
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from voice_tutor.sessions import SessionStore
from voice_tutor import app as module


def wav_payload():
    with BytesIO() as writer:
        sf.write(writer, 0.12 * np.sin(np.arange(16000) * (2 * np.pi * 330 / 16000)),
                 16000, format='WAV', subtype='PCM_16')
        return writer.getvalue()


def test_audio_persists_and_replay_never_synthesizes(tmp_path, monkeypatch):
    store = SessionStore(tmp_path / 'chat.sqlite3')
    monkeypatch.setattr(module, 'session_store', lambda: store)
    monkeypatch.setattr(module, 'voices', {'azusa_e36': {'id': 'azusa_e36'}})
    payload = wav_payload()
    calls = []
    async def fake_synth(settings, profile, text):
        calls.append(text)
        return payload
    monkeypatch.setattr(module, 'synthesize', fake_synth)
    monkeypatch.setattr(module.characters, 'tts_binding_matches', lambda: True)
    sid, mid = store.add_turn(None, 'こんにちは', {'reply_ja': '元気ですよ。', 'correction_ja': '', 'feedback_zh': ''}, return_id=True)
    url = f'/api/audio/{sid}/{mid}'
    with TestClient(module.app) as client:
        assert client.get(url).status_code == 404  # Never synthesized
        request = {'text': '元気ですよ。', 'session_id': sid, 'message_id': mid, 'voice_id': 'azusa_e36'}
        assert client.post('/api/speak', json=request).content == payload
        assert calls == ['元気ですよ。']
        assert client.post('/api/speak', json=request).content == payload  # cache hit
        assert calls == ['元気ですよ。']
        assert client.get(url).content == payload  # replay endpoint
        assert calls == ['元気ですよ。']
        assert client.get(f'/api/sessions/{sid}').json()['messages'][0]['audio_url']
        assert client.post('/api/speak', json={**request, 'text':'tampered'}).status_code == 409
        assert client.get(f'/api/audio/incorrect/{mid}').status_code == 404
        assert client.delete(f'/api/sessions/{sid}').status_code == 200
        assert client.get(url).status_code == 404
    assert not list(store.audio_dir.glob('*.wav'))


def test_scenes_removed_from_frontend_and_prompt():
    html=(Path(__file__).resolve().parents[1] / 'web/index.html').read_text(encoding='utf-8')
    from voice_tutor import conversation
    assert 'id="scene"' not in html
    assert 'data-topic=' not in html
    assert 'requestJson({text:val' not in html
    assert 'scene:' not in html
    assert 'scenario' not in conversation.SYSTEM.lower()
    assert '#81d8d0' in html.lower()
    assert '/api/audio/' in html
    assert 'async function playExistingAudio' in html


def test_generated_audio_survives_store_restart(tmp_path):
    store=SessionStore(tmp_path/'chat.sqlite3')
    sid, mid=store.add_turn(None,'こんにちは',{'reply_ja':'こんにちは！','correction_ja':'','feedback_zh':''},return_id=True)
    store.save_audio(sid,mid,'azusa_e36',wav_payload())
    reopened=SessionStore(tmp_path/'chat.sqlite3')
    assert reopened.get(sid)['messages'][0]['audio_url'] is not None
    assert reopened.audio_path(mid,'azusa_e36').is_file()


def test_conversation_mode_accepts_legacy_scene_but_ignores_it(monkeypatch):
    from voice_tutor.conversation import DeepSeekConversation
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):return {'choices':[{'message': {'content': json.dumps({'reply_ja':'こんにちは。','correction_ja':'','feedback_zh':''})}, 'finish_reason':'stop'}]}
    capture=[]
    class FakeClient:
        def __init__(self,*a,**k):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,url,headers,json):
            capture.append(json);return FakeResponse()
    from types import SimpleNamespace
    from voice_tutor import conversation
    monkeypatch.setattr(conversation.httpx,'AsyncClient',FakeClient)
    config=SimpleNamespace(api_key='test',model='test',base_url='https://example.com',timeout_seconds=2)
    assert asyncio.run(DeepSeekConversation(config).reply([], 'こんにちは', scene='interview'))['reply_ja']=='こんにちは。'
    assert 'interviewer' not in capture[0]['messages'][0]['content'].lower()
