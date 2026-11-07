"""Offline tests for provider JSON-mode empty output and text fallback."""

import asyncio
from types import SimpleNamespace

import pytest

from voice_tutor import conversation as c


def mock_chat(monkeypatch, completions):
    calls = []
    class Reply:
        def __init__(self, completion):
            self.completion = completion
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [self.completion]}
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is True
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, headers, json):
            calls.append(json)
            return Reply(completions[len(calls) - 1])
    monkeypatch.setattr(c.httpx, "AsyncClient", Client)
    return calls


def settings():
    return SimpleNamespace(api_key="fixture", model="deepseek-flash", base_url="https://api.deepseek.com", timeout_seconds=10)


def choice(content, finish_reason="stop"):
    return {"message": {"content": content}, "finish_reason": finish_reason}


def test_json_success_no_second_call(monkeypatch):
    calls = mock_chat(monkeypatch, [choice('{"reply_ja":"こんにちは。","correction_ja":"","feedback_zh":""}')])
    out = asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは"))
    assert out["reply_ja"] == "こんにちは。"
    assert len(calls) == 1
    assert calls[0]["response_format"]["type"] == "json_object"


def test_whitespace_json_then_structured_text(monkeypatch):
    calls = mock_chat(monkeypatch, [choice("  \n  "), choice('{"reply_ja":"はい、そうですね。","correction_ja":"","feedback_zh":""}')])
    out = asyncio.run(c.DeepSeekConversation(settings()).reply([
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは。"},
    ], "今日はどうですか"))
    assert out["reply_ja"] == "はい、そうですね。"
    assert [x["response_format"]["type"] for x in calls] == ["json_object", "text"]
    assert calls[0]["messages"][-3:] == calls[1]["messages"][-3:]


def test_whitespace_json_then_plain_japanese(monkeypatch):
    calls = mock_chat(monkeypatch, [choice(" "), choice("そうですね。今日は何をしたいですか？")])
    out = asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは"))
    assert out == {"reply_ja": "そうですね。今日は何をしたいですか？", "correction_ja": "", "feedback_zh": ""}
    assert len(calls) == 2


def test_correction_off_never_returns_feedback(monkeypatch):
    calls = mock_chat(monkeypatch, [choice('{"reply_ja":"はい。","correction_ja":"訂正","feedback_zh":"批评"}')])
    out = asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは", "off"))
    assert out == {"reply_ja": "はい。", "correction_ja": "", "feedback_zh": ""}
    assert len(calls) == 1


def test_both_blank_reports_usable_error(monkeypatch):
    calls = mock_chat(monkeypatch, [choice("  "), choice("\n ")])
    with pytest.raises(RuntimeError, match="no usable reply"):
        asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは"))
    assert len(calls) == 2


def test_invalid_json_then_no_json_fallback(monkeypatch):
    calls = mock_chat(monkeypatch, [choice('{"reply_ja":'), choice("ゆい先輩、こんにちは。")])
    out = asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは"))
    assert out["reply_ja"].startswith("ゆい先輩")
    assert len(calls) == 2


def test_length_truncation_uses_text_fallback(monkeypatch):
    calls = mock_chat(monkeypatch, [choice('{"reply_ja":"unfinished', "length"), choice("ええ、そうですね。")])
    out = asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは"))
    assert out["reply_ja"] == "ええ、そうですね。"
    assert len(calls) == 2


def test_text_fallback_does_not_expose_json_garbage(monkeypatch):
    mock_chat(monkeypatch, [choice(" "), choice('{"reply_ja":')])
    with pytest.raises(RuntimeError, match="no usable reply"):
        asyncio.run(c.DeepSeekConversation(settings()).reply([], "こんにちは"))
