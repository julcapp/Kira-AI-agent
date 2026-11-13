import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_local_commands():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        headers = {"X-API-Key": "test-key"}
        r = await c.post("/api/chat", headers=headers, json={"user_id":"alice","message":"/idea Первая идея"})
        assert r.status_code == 200
        assert "сохранена" in r.json()["reply"]
        r = await c.post("/api/chat", headers=headers, json={"user_id":"alice","message":"/list"})
        assert "Первая идея" in r.json()["reply"]
        r = await c.post("/api/chat", headers=headers, json={"user_id":"bob","message":"/list"})
        assert "Первая идея" not in r.json()["reply"]

@pytest.mark.asyncio
async def test_auth_and_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/chat", json={"user_id":"alice","message":"/agents"})
        assert r.status_code == 401
        h = {"X-API-Key":"test-key"}
        r = await c.post("/api/chat", headers=h, json={"user_id":"alice","message":"/agent tutor"})
        assert r.status_code == 200
        assert "Репетитор" in r.json()["reply"]
        r = await c.post("/api/chat", headers=h, json={"user_id":"alice","message":"Проведи урок"})
        assert "Репетитор" in r.json()["reply"]

@pytest.mark.asyncio
async def test_webhook_disabled():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/webhooks/max", json={})
        assert r.status_code == 503
