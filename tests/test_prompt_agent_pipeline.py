
import pytest
from app.skills import prompt_upgrader as upgrader
from app.config import settings


def test_original_has_priority():
    source = "Не публикуй пост, только подготовь черновик."
    combined = upgrader.agent_task_message(source, "Опубликуй пост сразу")
    assert source in combined
    assert combined.index(source) < combined.index("Опубликуй пост сразу")
    assert "если расходится с исходным запросом" in combined


def test_without_suggestion_original_unchanged():
    source = "Проверь только документацию"
    assert upgrader.agent_task_message(source, None) == source


@pytest.mark.asyncio
async def test_no_llm_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_model", "")
    assert await upgrader.prepare_for_agent("создай план", "Юрист") is None


@pytest.mark.asyncio
async def test_llm_failure_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid")
    monkeypatch.setattr(settings, "llm_api_key", "test")
    monkeypatch.setattr(settings, "llm_model", "test")
    async def broken(*args):
        raise RuntimeError("offline")
    monkeypatch.setattr(upgrader, "answer", broken)
    assert await upgrader.prepare_for_agent("создай план", "Юрист") is None


@pytest.mark.asyncio
async def test_structured_prompt_is_advisory(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid")
    monkeypatch.setattr(settings, "llm_api_key", "test")
    monkeypatch.setattr(settings, "llm_model", "test")
    observed = {}
    async def fake_answer(agent, instruction, prompt):
        observed.update(agent=agent, instruction=instruction, prompt=prompt)
        return "Цель: составить черновик"
    monkeypatch.setattr(upgrader, "answer", fake_answer)
    suggestion = await upgrader.prepare_for_agent("Только черновик; не публикуй", "VK SMM")
    combined = upgrader.agent_task_message("Только черновик; не публикуй", suggestion)
    assert "Не выполняй поручение" in observed["instruction"]
    assert "VK SMM" in observed["prompt"]
    assert "Только черновик; не публикуй" in combined
    assert "Цель: составить черновик" in combined


@pytest.mark.asyncio
async def test_overlong_skipped(monkeypatch):
    assert await upgrader.prepare_for_agent("x" * 8001, "Кирюша") is None
