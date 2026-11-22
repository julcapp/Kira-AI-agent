"""Library of approved skills; permissions are checked on every lookup.

This module intentionally does not execute prompts, tools or third-party code.
Persistence, RBAC and provider adapters are separate follow-up components.
"""
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class SkillStatus(str, Enum):
    draft = "draft"
    testing = "testing"
    approved = "approved"
    published = "published"
    retired = "retired"


class SkillSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    tenant_id: str = Field(min_length=1)
    slug: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,99}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)
    status: SkillStatus = SkillStatus.draft
    risk_level: str = Field(default="low", pattern=r"^(low|medium|high)$")
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    source_url: str | None = None
    license: str | None = None


class SkillGrant(BaseModel):
    model_config = ConfigDict(frozen=True)
    tenant_id: str = Field(min_length=1)
    agent_key: str = Field(min_length=1)
    slug: str = Field(min_length=3)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


class SkillsCatalog:
    def __init__(self):
        self._skills: dict[tuple[str, str, str], SkillSpec] = {}
        self._grants: set[tuple[str, str, str, str]] = set()

    def register(self, skill: SkillSpec) -> None:
        key = (skill.tenant_id, skill.slug, skill.version)
        if key in self._skills:
            raise ValueError("Skill version already exists; versions are immutable")
        self._skills[key] = skill

    def grant(self, assignment: SkillGrant) -> None:
        key = (assignment.tenant_id, assignment.slug, assignment.version)
        skill = self._skills.get(key)
        if not skill or skill.status != SkillStatus.published:
            raise ValueError("Only published skills may be granted")
        self._grants.add((assignment.tenant_id, assignment.agent_key,
                          assignment.slug, assignment.version))

    def resolve(self, *, tenant_id: str, agent_key: str,
                slug: str, version: str) -> SkillSpec:
        if (tenant_id, agent_key, slug, version) not in self._grants:
            raise PermissionError("Agent has no grant for this skill")
        skill = self._skills.get((tenant_id, slug, version))
        if skill is None or skill.status != SkillStatus.published:
            raise PermissionError("Skill is not published")
        return skill

    def available(self, *, tenant_id: str, agent_key: str) -> list[SkillSpec]:
        result = []
        for t, agent, slug, version in sorted(self._grants):
            if t == tenant_id and agent == agent_key:
                skill = self._skills.get((t, slug, version))
                if skill and skill.status == SkillStatus.published:
                    result.append(skill)
        return result
