import pytest
import httpx
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.config import settings
from app.db import SessionLocal, VoicePreference
from app.integrations.max_api import send_max_audio
from app.integrations.tts import synthesize_mp3, TTSUnavailable


def event(mid, text, user_id=42):
    return {"update_type": "message_created", "message": {
        "sender": {"user_id": user_id, "is_bot": False},
        "body": {"mid": mid, "text": text, "attachments": []}}}


@pytest.mark.asyncio
async def test_modes_are_persisted_and_voice_is_sent(monkeypatch):
    monkeypatch.setattr(settings, "max_enabled", True)
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    monkeypatch.setattr(settings, "max_webhook_secret", "test-secret")
    monkeypatch.setattr(settings, "max_allowed_user_ids", "42")
    sent_text, sent_audio = [], []
    async def fake_text(uid, text):
        sent_text.append((uid, text))
    async def fake_audio(uid, data):
        sent_audio.append((uid, data))
    async def fake_tts(text):
        return b"mock-mp3"
    monkeypatch.setattr("app.main.send_max_message", fake_text)
    monkeypatch.setattr("app.main.send_max_audio", fake_audio)
    monkeypatch.setattr("app.main.synthesize_mp3", fake_tts)
    headers = {"X-Max-Bot-Api-Secret": "test-secret"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for mid, msg in [("m1", "/voice both"), ("m2", "Запиши идею: мой план"),
                         ("m3", "/voice audio"), ("m4", "Создай задачу проверить план"),
                         ("m5", "/voice text"), ("m6", "/list")]:
            assert (await c.post("/webhooks/max", headers=headers, json=event(mid, msg))).status_code == 200
    with SessionLocal() as db:
        assert db.get(VoicePreference, "max:42").mode == "text"
    assert len(sent_text) == 4
    assert len(sent_audio) == 4
    assert sent_audio[-1] == (42, b"mock-mp3")


@pytest.mark.asyncio
async def test_tts_failure_falls_back_to_text(monkeypatch):
    monkeypatch.setattr(settings, "max_enabled", True)
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    monkeypatch.setattr(settings, "max_webhook_secret", "test-secret")
    monkeypatch.setattr(settings, "max_allowed_user_ids", "42")
    text_sent = []
    async def fake_text(uid, text):
        text_sent.append(text)
    async def failing_tts(text):
        raise TTSUnavailable("offline")
    monkeypatch.setattr("app.main.send_max_message", fake_text)
    monkeypatch.setattr("app.main.synthesize_mp3", failing_tts)
    headers = {"X-Max-Bot-Api-Secret": "test-secret"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/webhooks/max", headers=headers, json=event("m7", "/voice audio"))
    assert len(text_sent) == 1
    assert "Голосовой ответ сейчас недоступен" in text_sent[0]


@pytest.mark.asyncio
async def test_max_audio_upload_flow(monkeypatch):
    monkeypatch.setattr(settings, "max_enabled", True)
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path == "/uploads":
            assert request.url.params["type"] == "audio"
            return httpx.Response(200, json={"url": "https://omu.okcdn.ru/upload.do?x=1", "token": "media-token"})
        if request.url.host == "omu.okcdn.ru":
            assert b"kiryusha.mp3" in request.content
            return httpx.Response(200, text="<retval>1</retval>")
        assert request.url.path == "/messages"
        assert b"media-token" in request.content
        return httpx.Response(200, json={"message": {}})
    real_client = httpx.AsyncClient
    monkeypatch.setattr("app.integrations.max_api.httpx.AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    await send_max_audio(42, b"fake-audio")
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_tts_requires_configuration(monkeypatch):
    monkeypatch.setattr(settings, "tts_enabled", False)
    with pytest.raises(TTSUnavailable):
        await synthesize_mp3("Привет")
