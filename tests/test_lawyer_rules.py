from app.agents.legal_rules import LEGAL_SYSTEM_PROMPT, LEGAL_PROMPT_VERSION
from app.agents.registry import AGENTS, choose_agent

def test_legal_rules_active_in_registry():
    assert AGENTS["lawyer"].system == LEGAL_SYSTEM_PROMPT
    assert LEGAL_PROMPT_VERSION == "1.0.0"
    assert choose_agent("юрист, проверь договор") == "lawyer"

def test_legal_agent_requires_human_approval_and_real_sources():
    lower = LEGAL_SYSTEM_PROMPT.lower()
    for phrase in ("не выдумывай", "судебн", "провер", "подтвержд", "не отправляй", "юрисдикц"):
        assert phrase in lower

def test_lawyer_is_single_registered_agent():
    assert sum(key == "lawyer" for key in AGENTS) == 1
