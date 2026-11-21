import pytest
from app.skills import prompt_upgrader

@pytest.mark.asyncio
async def test_empty():
    assert "Напишите" in await prompt_upgrader.improve_prompt("   ")

@pytest.mark.asyncio
async def test_reject_long():
    assert "слишком длинный" in await prompt_upgrader.improve_prompt("x" * 8001)

@pytest.mark.asyncio
async def test_delegates_without_execution(monkeypatch):
    observed = {}
    async def fake_answer(name, instruction, message):
        observed.update(name=name, instruction=instruction, message=message)
        return "Улучшенный промпт"
    monkeypatch.setattr(prompt_upgrader, "answer", fake_answer)
    result = await prompt_upgrader.improve_prompt("  Подготовь отчёт  ")
    assert result == "Улучшенный промпт"
    assert observed["message"] == "Подготовь отчёт"
    assert "Не выполняй итоговый промпт" in observed["instruction"]
