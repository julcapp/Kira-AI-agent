"""Isolation, provenance and approval checks for catalogue foundations."""
import pytest
from app.skills import SkillSpec, SkillGrant, SkillsCatalog, SkillStatus
from app.brands import BrandFact, BrandPassport, BrandRegistry
from app.brands.passport import Sensitivity


def test_skill_requires_published_and_explicit_agent_grant():
    catalog = SkillsCatalog()
    draft = SkillSpec(tenant_id="company-a", slug="content.article-writing",
                      version="1.0.0", title="Автор статей")
    catalog.register(draft)
    with pytest.raises(ValueError):
        catalog.grant(SkillGrant(tenant_id="company-a", agent_key="article_author",
                                slug=draft.slug, version=draft.version))
    published = draft.model_copy(update={"version": "1.0.1", "status": SkillStatus.published})
    catalog.register(published)
    catalog.grant(SkillGrant(tenant_id="company-a", agent_key="article_author",
                            slug=published.slug, version=published.version))
    assert catalog.resolve(tenant_id="company-a", agent_key="article_author",
                           slug=published.slug, version="1.0.1") == published
    with pytest.raises(PermissionError):
        catalog.resolve(tenant_id="company-b", agent_key="article_author",
                        slug=published.slug, version="1.0.1")
    with pytest.raises(PermissionError):
        catalog.resolve(tenant_id="company-a", agent_key="marketer",
                        slug=published.slug, version="1.0.1")
    with pytest.raises(ValueError):
        catalog.register(published)


def test_passport_only_exposes_approved_facts_at_authorized_level():
    registry = BrandRegistry()
    registry.register(BrandPassport(
        tenant_id="company-a", brand_id="ice-cream", revision=1, title="У Тимоши",
        facts=(
            BrandFact(key="tagline", value="Стаканчик счастья", source="Approved brief",
                      sensitivity=Sensitivity.public, approved=True),
            BrandFact(key="budget", value="private", source="Internal ledger",
                      sensitivity=Sensitivity.confidential, approved=True),
            BrandFact(key="draft", value="unverified", source="Draft notes",
                      sensitivity=Sensitivity.public, approved=False),
        )))
    assert registry.context(tenant_id="company-a", brand_id="ice-cream",
                            allowed_levels={Sensitivity.public}) == {"tagline": "Стаканчик счастья"}
    with pytest.raises(KeyError):
        registry.context(tenant_id="company-b", brand_id="ice-cream",
                         allowed_levels={Sensitivity.public})
    with pytest.raises(ValueError):
        registry.register(BrandPassport(tenant_id="company-a",
                        brand_id="ice-cream", revision=1, title="Duplicate"))
