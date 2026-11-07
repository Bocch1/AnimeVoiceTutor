"""v0.9.4 regression tests: AI titles, pinned sessions, masked API keys."""
from pathlib import Path
import json
import sqlite3
from fastapi.testclient import TestClient
import pytest
from voice_tutor import app as module
from voice_tutor.sessions import SessionStore
from voice_tutor.llm_config import LLMConfigStore
from voice_tutor.conversation import parse_completion

class Defaults:
    api_key=''
    model='deepseek-flash'
    timeout_seconds=20


def test_legacy_migration_and_pinning(tmp_path):
    path=tmp_path/'sessions.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)')
        db.execute("INSERT INTO sessions VALUES ('legacy','用户旧标题','2026-01-01','2026-01-01')")
    store=SessionStore(path)
    assert store.get('legacy')['title']=='用户旧标题'
    sid,_=store.add_turn(None,'早上好',dict(reply_ja='こんにちは',correction_ja='',feedback_zh='',session_title='早晨问候'),return_id=True)
    assert store.get(sid)['title']=='早晨问候'
    assert store.set_pinned(sid,True)
    assert store.list_sessions()[0]['id']==sid
    assert store.get(sid)['is_pinned']==1
    assert SessionStore(path).get(sid)['is_pinned']==1
    assert store.set_pinned(sid,False)
    assert store.set_title('legacy','旅行规划')=='旅行规划'
    assert store.get('legacy')['title']=='旅行规划'
    assert not store.set_pinned('not-exist',True)


def test_first_reply_optional_title_and_json_fallback():
    d=parse_completion('{"reply_ja":"そうです","correction_ja":"","feedback_zh":"","session_title":"吉他练习心得"}')
    assert d['session_title']=='吉他练习心得'
    d=parse_completion('そうですね。',allow_plain_text=True)
    assert 'session_title' not in d


def test_public_key_suffix_mask_is_not_raw_secret(tmp_path):
    store=LLMConfigStore(tmp_path/'secrets.json',defaults=Defaults())
    original='SYNTHETIC_TEST_CREDENTIAL_ZX90'
    store.update('openai',api_key=original)
    info=store.public()['providers']['openai']
    assert info['has_api_key'] is True
    assert info['key_hint']=='••••••••ZX90'
    assert original not in json.dumps(store.public())
    assert original not in (tmp_path/'secrets.json').read_text()
    store.update('deepseek',api_key='short')
    assert store.public()['providers']['deepseek']['key_hint']=='••••••••'
    assert store.runtime().api_key=='short'


def test_pin_and_retitle_endpoints(tmp_path,monkeypatch):
    store=SessionStore(tmp_path/'db.sqlite3')
    sid,_=store.add_turn(None,'小语种课',dict(reply_ja='楽しいですね',correction_ja='',feedback_zh=''),return_id=True)
    monkeypatch.setattr(module,'session_store',lambda:store)
    async def mocked(self,turns):
        assert turns[0]['role']=='user'
        return '日语口语练习'
    monkeypatch.setattr(module.LLMConversation,'generate_title',mocked)
    with TestClient(module.app) as client:
        r=client.patch(f'/api/sessions/{sid}/pin',json={'pinned':True},headers={'Origin':'http://testserver'})
        assert r.status_code==200 and r.json()['is_pinned'] is True
        assert client.get('/api/sessions').json()['sessions'][0]['is_pinned']==1
        r=client.post(f'/api/sessions/{sid}/generate-title',json={},headers={'Origin':'http://testserver'})
        assert r.status_code==200 and r.json()['title']=='日语口语练习'
        assert store.get(sid)['title']=='日语口语练习'
        assert client.patch(f'/api/sessions/{sid}/pin',json={'pinned':False},headers={'Origin':'https://evil.example'}).status_code==403
        assert client.patch('/api/sessions/missing/pin',json={'pinned':True},headers={'Origin':'http://testserver'}).status_code==404


def test_sidebar_and_tail_wiring():
    html = (Path(__file__).parent.parent/'web/index.html').read_text(encoding='utf-8-sig')
    for key in ('id="llmKeyMask"', 'key_hint', 'session-more', 'session-menu', '/pin', 'id="roleAvatar"', 'class="manga-shape"'):
        assert key in html, key
    assert html.count('id="roleAvatar"') == 1
    assert html.count('viewBox="0 0 430 205"') == 2
    assert "sess.is_pinned?'pin-off':'pin'" in html
