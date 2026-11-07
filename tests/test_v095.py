"""Regression tests for v0.9.5 welcome, auto titles and greeting replay."""
import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from fastapi.testclient import TestClient
from voice_tutor import app as module
from voice_tutor.sessions import SessionStore
from voice_tutor.greetings import GREETING_BY_ID, GREETING_GROUPS


def test_greeting_catalog_has_time_groups():
    assert set(GREETING_GROUPS) == {'morning','afternoon','evening','night'}
    assert len(GREETING_BY_ID) >= 12
    assert any('おはよう' in t for t in (GREETING_BY_ID[x] for x in GREETING_BY_ID))
    assert any('こんばんは' in t for t in GREETING_BY_ID.values())
    assert all('…' not in text for text in GREETING_BY_ID.values())


def test_legacy_autotitle_migration_and_claim(tmp_path):
    db=tmp_path/'conv.sqlite3'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)')
        conn.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL,user_text TEXT NOT NULL,reply_ja TEXT NOT NULL,correction_ja TEXT NOT NULL,feedback_zh TEXT NOT NULL,created_at TEXT NOT NULL)')
        conn.execute("INSERT INTO sessions VALUES ('old','今日は元気ですか','2026-01-01','2026-01-02')")
        conn.execute("INSERT INTO messages(session_id,user_text,reply_ja,correction_ja,feedback_zh,created_at) VALUES('old','今日は元気ですか？','元気です','','','2026-01-02')")
        conn.execute("INSERT INTO sessions VALUES ('previous_ai','音乐与练习','2026-01-01','2026-01-01')")
        conn.execute("INSERT INTO messages(session_id,user_text,reply_ja,correction_ja,feedback_zh,created_at) VALUES('previous_ai','请问你好','こんにちは','','','2026-01-01')")
    store=SessionStore(db)
    assert store.get('old')['title_status']=='pending'
    assert store.get('previous_ai')['title_status']=='ai'
    assert store.claim_untitled()=='old'
    assert store.get('old')['title_status']=='processing'
    store.release_title_attempt('old')
    with store.connect() as db:
        assert db.execute("SELECT title_attempts FROM sessions WHERE id='old'").fetchone()[0]==1
    assert store.claim_untitled()=='old'
    assert store.set_title('old','日常问候')=='日常问候'
    assert store.get('old')['title_status']=='ai'
    assert store.claim_untitled() is None


def test_new_session_with_ai_title_not_reprocessed(tmp_path):
    store=SessionStore(tmp_path/'conv.sqlite3')
    sid,mid=store.add_turn(None,'早上好',{'reply_ja':'おはよう','correction_ja':'','feedback_zh':'','session_title':'早晨问候'},return_id=True)
    assert store.get(sid)['title_status']=='ai'
    assert store.claim_untitled() is None
    assert mid>0


def test_greeting_audio_synthesized_once_cached(tmp_path, monkeypatch):
    calls=[]
    async def fake_synth(settings, profile, text):
        calls.append(text)
        return b'RIFF'+b'\0'*128
    monkeypatch.setattr(module,'synthesize',fake_synth)
    monkeypatch.setattr(module,'voices',{'azusa_e36':{'id':'azusa_e36'}})
    monkeypatch.setattr(module,'settings',SimpleNamespace(store_path=tmp_path/'db.sqlite3'))
    module._greeting_locks.clear()
    with TestClient(module.app) as client:
        assert client.get('/api/greetings/missing/audio').status_code==404
        a=client.post('/api/greetings/morning_1/speak',json={},headers={'Origin':'http://testserver'})
        b=client.post('/api/greetings/morning_1/speak',json={},headers={'Origin':'http://testserver'})
        c=client.get('/api/greetings/morning_1/audio')
        assert a.status_code==b.status_code==c.status_code==200
        assert a.content==b.content==c.content
        assert calls==[GREETING_BY_ID['morning_1']]
        assert client.post('/api/greetings/morning_1/speak',json={},headers={'Origin':'https://evil.example'}).status_code==403


def test_browser_controls():
    html = (Path(__file__).parent.parent/'web/index.html').read_text(encoding='utf-8-sig')
    assert 'delete' in html.lower()
    assert "addAction('删除对话'" in html
    assert "addAction('AI 生成标题'" not in html
    assert 'function edgeArc(' in html
    assert 'greetingPlayBtn' in html
    assert '#send.send-btn:not(.hidden){background:#81d8d0' in html
    assert 'viewBox="0 0 430 205"' in html
    assert 'getHours()' in html


def test_auto_backfill_uses_ai_and_preserves_pin(tmp_path,monkeypatch):
    store=SessionStore(tmp_path/'conv.sqlite3')
    sid,mid=store.add_turn(None,'今日は元気？',{'reply_ja':'元気です','correction_ja':'','feedback_zh':''},return_id=True)
    assert store.get(sid)['title_status']=='pending'
    store.set_pinned(sid,True)
    monkeypatch.setattr(module,'session_store',lambda:store)
    monkeypatch.setattr(module.llm_config,'runtime',lambda:SimpleNamespace(api_key='key',provider='deepseek'))
    async def fake(self,turns):
        assert turns and turns[0]['content']=='今日は元気？'
        return '日常近况交流'
    monkeypatch.setattr(module.LLMConversation,'generate_title',fake)
    asyncio.run(module._finish_untitled_sessions())
    row=store.get(sid)
    assert row['title']=='日常近况交流'
    assert row['is_pinned']==1
    assert row['title_status']=='ai'
