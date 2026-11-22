"""Registration and routing tests for the Article Author agent."""
from app.agents.registry import AGENTS, choose_agent


def test_article_author_is_registered():
    author = AGENTS["article_author"]
    assert author.name == "Автор статей"
    assert "SEO" in author.description
    assert "источники" in author.system
    assert "подтверждения" in author.system


def test_article_author_routing():
    assert choose_agent("Написать статью про AI") == "article_author"
    assert choose_agent("Нужен копирайтер для блога") == "article_author"


def test_existing_agents_remain_available():
    assert {"competitors", "vk", "lawyer", "developer", "sales", "tutor"} <= set(AGENTS)
