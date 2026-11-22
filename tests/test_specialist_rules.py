from app.agents.registry import AGENTS, choose_agent
from app.agents.specialist_rules import (
    RULES_VERSION, ACCOUNTANT_PROMPT, REWRITER_PROMPT,
    PROGRAMMER_PROMPT, CODE_REVIEW_PROMPT, AD_WRITER_PROMPT
)
from app.agent_catalog import Catalog, initial_entries

def test_specialist_prompts_connected_to_registry():
    assert RULES_VERSION == "1.0.0"
    for key, prompt in (
        ("accountant", ACCOUNTANT_PROMPT),
        ("rewriter", REWRITER_PROMPT),
        ("developer", PROGRAMMER_PROMPT),
        ("code_review", CODE_REVIEW_PROMPT),
        ("ad_writer", AD_WRITER_PROMPT),
    ):
        assert AGENTS[key].system == prompt

def test_specialists_inside_six_categories():
    catalog=Catalog(initial_entries())
    assert len(catalog.children(None)) == 6
    assert catalog.resolve(("finance","accounting")).route == "accountant"
    assert catalog.resolve(("marketing","rewrite")).route == "rewriter"
    assert catalog.resolve(("marketing","advertisements")).route == "ad_writer"
    assert catalog.resolve(("developer","review")).route == "code_review"

def test_more_specific_intents_win():
    assert choose_agent("Сделай ревью кода") == "code_review"
    assert choose_agent("Перепиши текст, нужен рерайт") == "rewriter"
    assert choose_agent("Проверь бухгалтерскую ОСВ") == "accountant"

def test_cross_agent_safety_rules():
    assert "только после решения" in ACCOUNTANT_PROMPT
    assert "антиплагиат" in REWRITER_PROMPT
    assert "production" in PROGRAMMER_PROMPT
    assert "согласования" in CODE_REVIEW_PROMPT
    assert "подтверждения пользователя" in AD_WRITER_PROMPT
