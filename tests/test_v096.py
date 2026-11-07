"""Regression tests for custom confirmation dialog and natural greetings."""
from pathlib import Path
from voice_tutor.greetings import GREETING_BY_ID, GREETING_GROUPS
from voice_tutor import app as module


def test_no_hello_and_clock_groups():
    assert set(GREETING_GROUPS) == {"morning","afternoon","evening","night"}
    assert all(text.startswith("こんにちは。") for key,text in GREETING_BY_ID.items() if key.startswith("afternoon"))
    assert len(GREETING_BY_ID) == 16
    assert all("ございます" in text or "ください" in text or "ましょう" in text or "ます" in text for text in GREETING_BY_ID.values())
    assert all("話そうか？" not in text and "何をしようか？" not in text for text in GREETING_BY_ID.values())
    assert all("…" not in text for text in GREETING_BY_ID.values())


def test_page_modal_and_sidebar():
    html=(Path(__file__).parent.parent/"web/index.html").read_text(encoding="utf-8")
    assert 'role="alertdialog"' in html
    assert 'id="confirmOverlay"' in html
    assert 'await confirmAction(' in html
    assert "window.confirm(" not in html
    assert "if (!confirm(" not in html
    assert "if(!confirm(" not in html
    assert "#sidebar .sessions{padding-top:30px" in html
    assert "こんにちは" in html


def test_greeting_cache_key_changes_with_text(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(module,'settings',SimpleNamespace(store_path=tmp_path/'sessions.sqlite3'))
    first=module._greeting_audio_path('morning_1')
    assert first.suffix=='.wav'
    assert 'greeting_audio_cache' in str(first)
    assert 'morning_1' in first.name
    monkeypatch.setitem(GREETING_BY_ID,'morning_1','おはよう、別の台詞。')
    second=module._greeting_audio_path('morning_1')
    assert second!=first
