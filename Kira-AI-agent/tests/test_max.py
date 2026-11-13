import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.config import settings

@pytest.mark.asyncio
async def test_max_secret_allowlist_and_idempotency(monkeypatch):
    monkeypatch.setattr(settings, "max_enabled", True)
    monkeypatch.setattr(settings, "max_bot_token", "fake-token")
    monkeypatch.setattr(settings, "max_webhook_secret", "test-webhook-secret")
    monkeypatch.setattr(settings, "max_allowed_user_ids", "42")
    sent = []
    async def fake_send(uid, text):
        sent.append((uid, text))
    monkeypatch.setattr("app.main.send_max_message", fake_send)
    payload = {"update_type":"message_created",
               "message":{"sender":{"user_id":42,"is_bot":False},
                          "body":{"mid":"message-001","text":"/idea Тест MAX"}}}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.post("/webhooks/max",json=payload)).status_code == 403
        header = {"X-Max-Bot-Api-Secret":"test-webhook-secret"}
        assert (await client.post("/webhooks/max",json=payload,headers=header)).status_code == 200
        duplicate = await client.post("/webhooks/max",json=payload,headers=header)
        assert duplicate.json().get("duplicate") is True
        assert len(sent) == 1
