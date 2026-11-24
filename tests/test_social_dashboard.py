from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from test_miniapp import make_data

def test_social_dashboard(monkeypatch):
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    monkeypatch.setattr(settings, "max_allowed_user_ids", "42")
    client = TestClient(app)
    path = "/api/mini/social/channels"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-Max-Init-Data": make_data(user_id=99)}).status_code == 403
    response = client.get(path, headers={"X-Max-Init-Data": make_data()})
    assert response.status_code == 200
    channels = response.json()["channels"]
    assert len(channels) == 11
    assert all(not c["connected"] and not c["publish"] and c["manual_draft"] for c in channels)
    assert "social-list" in client.get("/app").text
