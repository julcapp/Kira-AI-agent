from app.skills.registry import SKILLS, skill_instructions_for_agent, _read_skill_asset
import pytest

def test_competitor_skill_is_versioned_and_scoped():
    spec = SKILLS["competitor-profiling"]
    assert spec.version == "2.0.1"
    assert spec.agent_keys == ("competitors",)
    assert "name: competitor-profiling" in _read_skill_asset(spec.slug, spec.main)

def test_only_competitor_agent_gets_skill():
    assert "Shared skill: competitor-profiling v2.0.1" in skill_instructions_for_agent("competitors")
    assert skill_instructions_for_agent("lawyer") == ""
    assert skill_instructions_for_agent("kiryusha") == ""

def test_reference_files_available():
    spec = SKILLS["competitor-profiling"]
    assert all(_read_skill_asset(spec.slug, path) for path in spec.references)

def test_directory_traversal_blocked():
    with pytest.raises(ValueError):
        _read_skill_asset("competitor-profiling", "../../config.py")

def test_provider_connectors_not_enabled():
    assert all(item.endswith(":planned") for item in SKILLS["competitor-profiling"].external_integrations)
