"""Owner-scoped API for completed jobs and specialist steps."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from ..miniapp_auth import validate_init_data
from ..db import SessionLocal
from .models import WorkJob
from .service import create_job, serialize_job

router = APIRouter(prefix="/api/mini/work", tags=["work"])


def owner_from_max(x_max_init_data: str = Header(default="")) -> str:
    return validate_init_data(x_max_init_data)


class SubmitJob(BaseModel):
    request: str = Field(min_length=1, max_length=5000)


@router.post("/jobs", status_code=202)
def submit(data: SubmitJob, owner: str = Depends(owner_from_max)):
    with SessionLocal() as db:
        job = create_job(db, owner=owner, request=data.request, source="mini")
        return serialize_job(db, job)


@router.get("/jobs")
def jobs(owner: str = Depends(owner_from_max)):
    with SessionLocal() as db:
        rows = db.scalars(select(WorkJob).where(WorkJob.owner_id == owner)
                          .order_by(WorkJob.id.desc()).limit(50)).all()
        return {"jobs": [{"id": j.id, "status": j.status,
                          "request": j.request[:300], "source": j.source}
                         for j in rows]}


@router.get("/jobs/{job_id}")
def job_detail(job_id: int, owner: str = Depends(owner_from_max)):
    with SessionLocal() as db:
        job = db.get(WorkJob, job_id)
        if job is None or job.owner_id != owner:
            raise HTTPException(404, "Job not found")
        return serialize_job(db, job)
