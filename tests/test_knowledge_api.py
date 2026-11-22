"""Knowledge API requires valid MAX identity and server-side tenant grants."""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db import SessionLocal
from app.knowledge.models import TenantMembership
from app.knowledge import api


@pytest.mark.asyncio
async def test_tenant_isolation_and_publication_workflow(monkeypatch):
    monkeypatch.setattr(api, "validate_init_data",
                        lambda raw: "max:42" if raw == "signed-user" else "max:99")
    with SessionLocal() as db:
        db.add(TenantMembership(tenant_id="one", owner_id="max:42", role="owner"))
        db.add(TenantMembership(tenant_id="two", owner_id="max:99", role="owner"))
        db.commit()
    headers = {"X-MAX-Init-Data": "signed-user"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get("/api/mini/knowledge/two/skills", headers=headers)
        assert denied.status_code == 403

        created = await client.post("/api/mini/knowledge/one/skills", headers=headers,
                                    json={"slug": "content.article-writing", "version": "1.0.0",
                                          "title": "Автор статей"})
        assert created.status_code == 201, created.text
        duplicate = await client.post("/api/mini/knowledge/one/skills", headers=headers,
                                      json={"slug": "content.article-writing", "version": "1.0.0",
                                            "title": "Автор статей"})
        assert duplicate.status_code == 409

        grant = await client.post("/api/mini/knowledge/one/skills/content.article-writing/1.0.0/grants",
                                  headers=headers, json={"agent_key": "article_author"})
        assert grant.status_code == 409

        path = "/api/mini/knowledge/one/skills/content.article-writing/1.0.0/advance"
        for expected in ("testing", "approved", "published"):
            response = await client.post(path, headers=headers)
            assert response.status_code == 200, response.text
            assert response.json()["status"] == expected
        assert (await client.post(path, headers=headers)).status_code == 409

        granted = await client.post("/api/mini/knowledge/one/skills/content.article-writing/1.0.0/grants",
                                    headers=headers, json={"agent_key": "article_author"})
        assert granted.status_code == 201, granted.text
        available = await client.get("/api/mini/knowledge/one/agents/article_author/skills", headers=headers)
        assert available.status_code == 200
        assert available.json()["skills"][0]["slug"] == "content.article-writing"
        assert (await client.get("/api/mini/knowledge/two/agents/article_author/skills", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_brand_facts_are_approved_and_tenant_scoped(monkeypatch):
    monkeypatch.setattr(api, "validate_init_data", lambda _: "max:42")
    with SessionLocal() as db:
        db.add(TenantMembership(tenant_id="one", owner_id="max:42", role="owner"))
        db.commit()
    headers = {"X-MAX-Init-Data": "signed"}
    facts = [
        {"key": "slogan", "value": "Стаканчик счастья", "source": "Approved brief",
         "sensitivity": "public", "approved": True},
        {"key": "draft", "value": "unverified", "source": "Draft",
         "sensitivity": "public", "approved": False},
    ]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.post("/api/mini/knowledge/one/brands", headers=headers,
                                  json={"brand_id": "ice", "revision": 1, "title": "У Тимоши",
                                        "facts": facts})).status_code == 201
        ctx = await client.get("/api/mini/knowledge/one/brands/ice/context", headers=headers)
        assert ctx.status_code == 200
        assert ctx.json()["facts"] == {"slogan": "Стаканчик счастья"}
        assert (await client.get("/api/mini/knowledge/other/brands/ice/context", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_editor_cannot_publish_or_approve_facts(monkeypatch):
    monkeypatch.setattr(api, "validate_init_data", lambda _: "max:10")
    with SessionLocal() as db:
        db.add(TenantMembership(tenant_id="one", owner_id="max:10", role="editor"))
        db.commit()
    headers = {"X-MAX-Init-Data": "signed"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/mini/knowledge/one/skills", headers=headers,
                              json={"slug": "content.article-writing", "version": "1.0.0",
                                    "title": "Статья"})
        assert r.status_code == 201
        path = "/api/mini/knowledge/one/skills/content.article-writing/1.0.0/advance"
        assert (await client.post(path, headers=headers)).json()["status"] == "testing"
        assert (await client.post(path, headers=headers)).status_code == 403
        r = await client.post("/api/mini/knowledge/one/brands", headers=headers,
                              json={"brand_id": "brand", "revision": 1, "title": "Brand",
                                    "facts": [{"key": "claim", "value": "Unapproved", "source": "Editor",
                                               "approved": True, "sensitivity": "public"}]})
        assert r.status_code == 201
        ctx = await client.get("/api/mini/knowledge/one/brands/brand/context", headers=headers)
        assert ctx.json()["facts"] == {}
