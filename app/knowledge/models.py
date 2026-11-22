"""Persistent tenant-scoped knowledge models. No third-party skill code execution."""
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def utcnow():
    return datetime.now(timezone.utc)


class TenantMembership(Base):
    __tablename__ = "knowledge_memberships"
    tenant_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    __table_args__ = (Index("ix_knowledge_memberships_owner", "owner_id"),)


class SkillVersion(Base):
    __tablename__ = "knowledge_skill_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("tenant_id", "slug", "version", name="uq_knowledge_skill_version"),
                      UniqueConstraint("id", "tenant_id", name="uq_knowledge_skill_id_tenant"),
                      Index("ix_knowledge_skills_tenant", "tenant_id"),)


class AgentSkillGrant(Base):
    __tablename__ = "knowledge_agent_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_key: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("tenant_id", "agent_key", "skill_id", name="uq_knowledge_agent_grant"),
                      ForeignKeyConstraint(["skill_id", "tenant_id"],
                                           ["knowledge_skill_versions.id", "knowledge_skill_versions.tenant_id"],
                                           ondelete="CASCADE"),
                      Index("ix_knowledge_grants_tenant_agent", "tenant_id", "agent_key"))


class BrandRevision(Base):
    __tablename__ = "knowledge_brand_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    brand_id: Mapped[str] = mapped_column(String(100), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    facts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("tenant_id", "brand_id", "revision", name="uq_knowledge_brand_revision"),
                      Index("ix_knowledge_brands_tenant_brand", "tenant_id", "brand_id"))


class KnowledgeAudit(Base):
    __tablename__ = "knowledge_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_key: Mapped[str] = mapped_column(String(240), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (Index("ix_knowledge_audit_tenant_time", "tenant_id", "created_at"),)
