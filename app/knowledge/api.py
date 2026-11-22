"""MAX-authenticated knowledge API with explicit server-side tenant memberships."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from ..db import SessionLocal
from ..miniapp_auth import validate_init_data
from ..skills.registry import SkillSpec, SkillStatus
from ..brands.passport import BrandPassport, Sensitivity
from .models import TenantMembership, SkillVersion, AgentSkillGrant, BrandRevision, KnowledgeAudit

from fastapi import Header

router = APIRouter(prefix="/api/mini/knowledge", tags=["Knowledge"])


def current_owner(x_max_init_data: str = Header(default="")) -> str:
    return validate_init_data(x_max_init_data)


def authorize(db, tenant_id: str, owner_id: str, roles: set[str]) -> TenantMembership:
    member = db.get(TenantMembership, (tenant_id, owner_id))
    if member is None or member.role not in roles:
        raise HTTPException(403, "No permission for this organization")
    return member


def audit(db, tenant_id: str, owner_id: str, action: str, object_key: str):
    db.add(KnowledgeAudit(tenant_id=tenant_id, actor_id=owner_id,
                          action=action, object_key=object_key))


class CreateSkill(BaseModel):
    slug: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,99}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)
    risk_level: str = Field(default="low", pattern=r"^(low|medium|high)$")
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    source_url: str | None = None
    license: str | None = Field(default=None, max_length=200)


class CreateBrand(BaseModel):
    brand_id: str = Field(pattern=r"^[a-zA-Z0-9_.-]{2,100}$")
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    facts: list = Field(default_factory=list)


class GrantSkill(BaseModel):
    agent_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,79}$")


@router.get("/{tenant_id}/skills")
def list_skills(tenant_id: str, owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        authorize(db, tenant_id, owner, {"owner", "editor", "viewer"})
        rows = db.scalars(select(SkillVersion).where(SkillVersion.tenant_id == tenant_id)
                          .order_by(SkillVersion.slug, SkillVersion.version)).all()
        return {"skills": [{"slug": s.slug, "version": s.version, "title": s.title,
                            "status": s.status, "risk_level": s.risk_level} for s in rows]}


@router.post("/{tenant_id}/skills", status_code=201)
def create_skill(tenant_id: str, data: CreateSkill, owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        authorize(db, tenant_id, owner, {"owner", "editor"})
        spec = SkillSpec(tenant_id=tenant_id, **data.model_dump())
        row = SkillVersion(**spec.model_dump(mode="json"))
        db.add(row)
        audit(db, tenant_id, owner, "skill_create", f"{spec.slug}:{spec.version}")
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Skill version exists")
        return {"slug": spec.slug, "version": spec.version, "status": "draft"}


@router.post("/{tenant_id}/skills/{slug}/{version}/advance")
def advance_skill(tenant_id: str, slug: str, version: str, owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        membership = authorize(db, tenant_id, owner, {"owner", "editor"})
        row = db.scalar(select(SkillVersion).where(SkillVersion.tenant_id == tenant_id,
                         SkillVersion.slug == slug, SkillVersion.version == version))
        if row is None:
            raise HTTPException(404, "Skill not found")
        transitions = {"draft": "testing", "testing": "approved", "approved": "published"}
        next_status = transitions.get(row.status)
        if not next_status:
            raise HTTPException(409, "No further transition")
        # Only an organization owner may approve or publish a version.
        if next_status in {"approved", "published"} and membership.role != "owner":
            raise HTTPException(403, "Owner approval required")
        row.status = next_status
        audit(db, tenant_id, owner, "skill_advance", f"{slug}:{version}:{next_status}")
        db.commit()
        return {"status": next_status}


@router.post("/{tenant_id}/skills/{slug}/{version}/grants", status_code=201)
def grant_skill(tenant_id: str, slug: str, version: str, data: GrantSkill,
                owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        authorize(db, tenant_id, owner, {"owner"})
        skill = db.scalar(select(SkillVersion).where(SkillVersion.tenant_id == tenant_id,
                          SkillVersion.slug == slug, SkillVersion.version == version))
        if skill is None or skill.status != SkillStatus.published.value:
            raise HTTPException(409, "Skill must be published")
        db.add(AgentSkillGrant(tenant_id=tenant_id, agent_key=data.agent_key, skill_id=skill.id))
        audit(db, tenant_id, owner, "skill_grant", f"{slug}:{version}:{data.agent_key}")
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Grant already exists")
        return {"agent_key": data.agent_key, "slug": slug, "version": version}


@router.get("/{tenant_id}/agents/{agent_key}/skills")
def agent_skills(tenant_id: str, agent_key: str, owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        authorize(db, tenant_id, owner, {"owner", "editor", "viewer"})
        rows = db.scalars(select(SkillVersion).join(AgentSkillGrant,
                          (AgentSkillGrant.skill_id == SkillVersion.id) &
                          (AgentSkillGrant.tenant_id == SkillVersion.tenant_id))
                          .where(AgentSkillGrant.tenant_id == tenant_id,
                                 AgentSkillGrant.agent_key == agent_key,
                                 SkillVersion.status == SkillStatus.published.value)).all()
        return {"skills": [{"slug": s.slug, "version": s.version, "title": s.title} for s in rows]}


@router.post("/{tenant_id}/brands", status_code=201)
def create_brand(tenant_id: str, data: CreateBrand, owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        membership = authorize(db, tenant_id, owner, {"owner", "editor"})
        passport = BrandPassport(tenant_id=tenant_id, **data.model_dump())
        latest = db.scalar(select(func.max(BrandRevision.revision)).where(
            BrandRevision.tenant_id == tenant_id, BrandRevision.brand_id == passport.brand_id))
        if (latest or 0) >= passport.revision:
            raise HTTPException(409, "Revision must increase")
        facts = [fact.model_dump(mode="json") for fact in passport.facts]
        # Editors can propose facts, but cannot mark any of them as approved.
        if membership.role != "owner":
            for fact in facts:
                fact["approved"] = False
        db.add(BrandRevision(tenant_id=tenant_id, brand_id=passport.brand_id,
                             revision=passport.revision, title=passport.title, facts=facts))
        audit(db, tenant_id, owner, "brand_revision", f"{passport.brand_id}:{passport.revision}")
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Duplicate revision")
        return {"brand_id": passport.brand_id, "revision": passport.revision}


@router.get("/{tenant_id}/brands/{brand_id}/context")
def brand_context(tenant_id: str, brand_id: str, owner: str = Depends(current_owner)):
    with SessionLocal() as db:
        membership = authorize(db, tenant_id, owner, {"owner", "editor", "viewer"})
        row = db.scalar(select(BrandRevision).where(
            BrandRevision.tenant_id == tenant_id, BrandRevision.brand_id == brand_id)
            .order_by(BrandRevision.revision.desc()).limit(1))
        if row is None:
            raise HTTPException(404, "Brand not found")
        allowed = ({Sensitivity.public.value, Sensitivity.internal.value,
                    Sensitivity.confidential.value, Sensitivity.restricted.value}
                   if membership.role == "owner" else
                   {Sensitivity.public.value, Sensitivity.internal.value})
        facts = {f["key"]: f["value"] for f in row.facts
                 if f.get("approved") and f.get("sensitivity") in allowed}
        return {"brand_id": brand_id, "revision": row.revision, "facts": facts}
