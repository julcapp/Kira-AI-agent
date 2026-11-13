import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.integrations.max_api import parse_incoming, extract_message_text


def event(mid, attachments=None, text=None):
    return {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 42, "is_bot": False},
            "body": {"mid": mid, "text": text, "attachments": attachments or []},
        },
    }


def test_voice_transcript_extraction():
    audio = [{"type": "audio", "payload": {"transcription": "Запиши идею: новый проект"}}]
    assert parse_incoming(event("v1", attachments=audio)) == (42, "Запиши идею: новый проект", "v1")
    assert extract_message_text({"text": "обычный текст", "attachments": audio}) == "обычный текст"
    assert parse_incoming(event("v2", attachments=[{"type": "audio", "payload": {}}]))[1] == "/voice_unavailable"
    assert parse_incoming(event("v3", attachments=[{"type": "image", "payload": {}}])) is None


@pytest.mark.asyncio
async def test_voice_idea_and_agent_switch(monkeypatch):
    monkeypatch.setattr(settings, "max_enabled", True)
    monkeypatch.setattr(settings, "max_bot_token", "fake-token")
    monkeypatch.setattr(settings, "max_webhook_secret", "secret")
    monkeypatch.setattr(settings, "max_allowed_user_ids", "42")
    sent = []
    async def fake_send(uid, text):
        sent.append(text)
    monkeypatch.setattr("app.main.send_max_message", fake_send)
    headers = {"X-Max-Bot-Api-Secret": "secret"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for mid, transcript in [("v1", "Запиши идею: новый проект"),
                                ("v2", "Переключи на юриста"),
                                ("v3", "Создай задачу проверить договор")]:
            audio = [{"type": "audio", "payload": {"transcription": transcript}}]
            resp = await client.post("/webhooks/max", headers=headers, json=event(mid, audio))
            assert resp.status_code == 200
        r = await client.post("/webhooks/max", headers=headers, json=event("v4", [{"type": "audio", "payload": {}}]))
        assert r.status_code == 200
        assert "Идея" in sent[0] and "новый проект" in sent[0]
        assert "Юрист" in sent[1]
        assert "Задача" in sent[2]
        assert "не прислал расшифровку" in sent[3]
