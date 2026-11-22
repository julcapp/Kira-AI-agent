"""Brand facts have explicit provenance and sensitivity classifications.

A passport is not a storage location for customer personal data or credentials.
"""
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class Sensitivity(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class BrandFact(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=5000)
    source: str = Field(min_length=1, max_length=1000)
    verified_at: str | None = None
    sensitivity: Sensitivity = Sensitivity.internal
    approved: bool = False


class BrandPassport(BaseModel):
    model_config = ConfigDict(frozen=True)
    tenant_id: str = Field(min_length=1)
    brand_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    facts: tuple[BrandFact, ...] = ()


class BrandRegistry:
    def __init__(self):
        self._passports: dict[tuple[str, str, int], BrandPassport] = {}

    def register(self, passport: BrandPassport) -> None:
        key = (passport.tenant_id, passport.brand_id, passport.revision)
        if key in self._passports:
            raise ValueError("Brand revision already exists; revisions are immutable")
        earlier = [rev for tenant, brand, rev in self._passports
                   if tenant == passport.tenant_id and brand == passport.brand_id]
        if earlier and passport.revision <= max(earlier):
            raise ValueError("Revision must increase")
        self._passports[key] = passport

    def context(self, *, tenant_id: str, brand_id: str,
                allowed_levels: set[Sensitivity]) -> dict[str, str]:
        # Missing scope must never fall back to another tenant or brand.
        versions = [p for (tenant, brand, _), p in self._passports.items()
                    if tenant == tenant_id and brand == brand_id]
        if not versions:
            raise KeyError("Brand passport not found")
        latest = max(versions, key=lambda p: p.revision)
        return {fact.key: fact.value for fact in latest.facts
                if fact.approved and fact.sensitivity in allowed_levels}
