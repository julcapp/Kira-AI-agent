"""Safe, deterministic specialist delegation (text output only).

This MVP does not run tools or perform external business actions. No LLM credentials
means jobs fail explicitly, rather than returning demo text as a completed result.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..agents.registry import AGENTS, choose_agent
from ..config import settings
from ..llm import answer
from .models import WorkJob, WorkStep, WorkNotice


def plan_agents(request: str) -> list[str]:
    """Select no more than three distinct existing specialists by task vocabulary."""
    text = request.lower()
    groups = (
        ("competitors", ("конкурент", "рынок", "сравни компании")),
        ("vk", ("реклам", "маркетинг", "контент", "vk", "вк", "пост")),
        ("lawyer", ("договор", "юрист", "правов", "претензи")),
        ("developer", ("код", "разработ", "сайт", "api", "тест")),
        ("sales", ("продаж", "клиент", "коммерческ")),
        ("tutor", ("обучен", "урок", "преподавател")),
    )
    found = [key for key, words in groups if any(w in text for w in words)]
    if not found:
        selected = choose_agent(request)
        found = [selected] if selected in AGENTS else []
    return found[:3]  # Explicit, reviewable cap on workload and token costs.


def create_job(db: Session, *, owner: str, request: str, source: str) -> WorkJob:
    request = request.strip()
    if not (1 <= len(request) <= 5000):
        raise ValueError("Request must be 1..5000 characters")
    if source not in ("max", "mini", "local"):
        raise ValueError("Unsupported source")
    agents = plan_agents(request)
    job = WorkJob(owner_id=owner, request=request, source=source,
                  status="queued" if agents else "needs_clarification")
    db.add(job)
    db.flush()
    for position, agent_key in enumerate(agents):
        db.add(WorkStep(job_id=job.id, position=position,
                        agent_key=agent_key, request=request))
    if not agents:
        job.result = "Уточните, какого результата ожидаете, или укажите направление задачи."
    db.commit()
    db.refresh(job)
    return job


def serialize_job(db: Session, job: WorkJob) -> dict:
    steps = db.scalars(select(WorkStep).where(WorkStep.job_id == job.id)
                       .order_by(WorkStep.position)).all()
    return {"id": job.id, "status": job.status, "source": job.source,
            "request": job.request, "result": job.result, "error": job.error,
            "steps": [{"agent": s.agent_key, "status": s.status,
                       "result": s.result} for s in steps]}


async def work_once() -> bool:
    """Claim one job in a transaction; safe against competing PostgreSQL workers.

    Stale processing leases and dead-letter handling are future requirements.
    """
    from ..db import SessionLocal
    with SessionLocal() as db:
        job = db.scalar(select(WorkJob).where(WorkJob.status == "queued")
                        .order_by(WorkJob.id).with_for_update(skip_locked=True).limit(1))
        if job is None:
            return False
        job.status = "processing"
        job.attempts += 1
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        job_id = job.id
    with SessionLocal() as db:
        job = db.get(WorkJob, job_id)
        steps = db.scalars(select(WorkStep).where(WorkStep.job_id == job_id)
                           .order_by(WorkStep.position)).all()
        try:
            if not (settings.llm_base_url and settings.llm_api_key and settings.llm_model):
                raise RuntimeError("LLM provider not configured")
            outputs = []
            for step in steps:
                step.status = "processing"
                db.commit()
                specialist = AGENTS[step.agent_key]
                value = await answer(specialist.name, specialist.system,
                                     "Подготовь только информационный результат для задачи: " + step.request)
                if not value or not value.strip():
                    raise RuntimeError("Empty specialist output")
                step.result, step.status = value, "completed"
                outputs.append(f"{specialist.name}:\n{value}")
                db.commit()
            job.result = "\n\n".join(outputs)
            job.status = "completed"
            job.error = None
        except Exception:
            # Do not claim success after partial results or provider errors.
            job.status = "failed"
            job.error = "Исполнение не завершено. Проверьте подключение LLM и повторите позднее."
            for step in steps:
                if step.status == "processing":
                    step.status = "failed"
        job.updated_at = datetime.now(timezone.utc)
        if job.owner_id.startswith("max:"):
            db.add(WorkNotice(job_id=job.id, owner_id=job.owner_id,
                              message=(f"Задача #{job.id}: {job.status}. "
                                       "Откройте результат в Mini App или отправьте /job "
                                       f"{job.id} для просмотра.")))
        db.commit()
    return True


async def deliver_once() -> bool:
    """At-least-once MAX notification. Duplicate delivery is possible on crash."""
    from ..db import SessionLocal
    from ..integrations.max_api import send_max_message
    if not settings.max_enabled:
        return False
    with SessionLocal() as db:
        notice = db.scalar(select(WorkNotice).where(WorkNotice.delivered_at.is_(None),
                          WorkNotice.attempts < 3).order_by(WorkNotice.id)
                          .with_for_update(skip_locked=True).limit(1))
        if notice is None:
            return False
        notice.attempts += 1
        db.commit()
        try:
            await send_max_message(int(notice.owner_id.split(":", 1)[1]), notice.message)
            notice.delivered_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
        return True
