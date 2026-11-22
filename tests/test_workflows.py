"""Persistent orchestration: queue, ownership, voice path, worker and no fake success."""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db import SessionLocal
from app.workflows.models import WorkJob, WorkStep, WorkNotice
from app.workflows.service import create_job, work_once
from app.core.orchestrator import handle_message
from app.config import settings
from app.workflows import api


@pytest.mark.asyncio
async def test_voice_delegate_and_owner_scoped_result():
    with SessionLocal() as db:
        text = await handle_message(db, "max:42", "Кира поручаю: проанализировать конкурентов и подготовить рекламу")
        assert "Задача #1 принята" in text
        job = db.get(WorkJob, 1)
        assert job.status == "queued"
        agents = [step.agent_key for step in db.query(WorkStep).order_by(WorkStep.position)]
        assert agents == ["competitors", "vk"]
        assert "не найдена" in await handle_message(db, "max:99", "/job 1")
        assert "queued" in await handle_message(db, "max:42", "/job 1")


@pytest.mark.asyncio
async def test_missing_provider_must_fail_and_notify(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "")
    with SessionLocal() as db:
        create_job(db, owner="max:42", request="Сделай маркетинговый анализ", source="max")
    assert await work_once() is True
    with SessionLocal() as db:
        job = db.query(WorkJob).one()
        assert job.status == "failed"
        assert not job.result
        assert db.query(WorkNotice).count() == 1


@pytest.mark.asyncio
async def test_worker_combines_two_specialists(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(settings, "llm_api_key", "fake")
    monkeypatch.setattr(settings, "llm_model", "fake")
    async def fake_answer(name, system, request):
        return "Черновик: " + name
    monkeypatch.setattr("app.workflows.service.answer", fake_answer)
    with SessionLocal() as db:
        create_job(db, owner="max:42", request="Сравни конкурентов и сделай рекламный текст", source="max")
    assert await work_once() is True
    with SessionLocal() as db:
        job = db.query(WorkJob).one()
        assert job.status == "completed"
        assert "Аналитик конкурентов" in job.result
        assert "VK SMM" in job.result
        assert db.query(WorkStep).filter(WorkStep.status == "completed").count() == 2


@pytest.mark.asyncio
async def test_signed_api_requires_identity_and_scopes_by_owner(monkeypatch):
    monkeypatch.setattr(api, "validate_init_data",
                        lambda raw: "max:42" if raw == "valid" else "max:99")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        posted = await client.post("/api/mini/work/jobs",
                                   headers={"X-MAX-Init-Data": "valid"},
                                   json={"request": "Анализ конкурентов"})
        assert posted.status_code == 202, posted.text
        job_id = posted.json()["id"]
        denied = await client.get(f"/api/mini/work/jobs/{job_id}",
                                  headers={"X-MAX-Init-Data": "other"})
        assert denied.status_code == 404
        listed = await client.get("/api/mini/work/jobs", headers={"X-MAX-Init-Data": "valid"})
        assert len(listed.json()["jobs"]) == 1
