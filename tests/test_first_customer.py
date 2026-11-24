from app.skills.registry import SKILLS, skill_instructions_for_agent, _read_skill_asset

def test_first_customer_scope():
    spec = SKILLS["first-customer"]
    assert spec.version == "1.0.0"
    assert spec.agent_keys == ("sales",)
    assert not spec.external_integrations
    assert "Shared skill: first-customer v1.0.0" in skill_instructions_for_agent("sales")
    for agent in ("competitors", "lawyer", "kiryusha", "vk"):
        assert "first-customer" not in skill_instructions_for_agent(agent)
    assert all(_read_skill_asset(spec.slug, path) for path in spec.references)

def test_first_customer_draft_only():
    instructions = skill_instructions_for_agent("sales")
    assert "Не отправляй сообщения" in instructions
    assert "переход только после согласования" in instructions
