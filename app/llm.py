import httpx
from .config import settings

async def answer(agent_name: str, instruction: str, message: str) -> str:
    if not (settings.llm_base_url and settings.llm_api_key and settings.llm_model):
        return (
            f"🧠 {agent_name} (деморежим). Получил запрос: {message[:800]}\n"
            "Для генерации полноценного ответа подключи LLM_BASE_URL, LLM_API_KEY и LLM_MODEL. "
            "Пока доступны сохранение задач, идей, переключение агентов и напоминания."
        )
    # The base URL is a TRUSTED operator-controlled endpoint, not user input.
    endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": instruction + "\nНе выполняй внешних действий и не утверждай, что они выполнены."},
            {"role": "user", "content": message[:12000]},
        ],
        "temperature": 0.3,
        "max_tokens": 1200,
    }
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(endpoint, json=payload, headers={"Authorization": f"Bearer {settings.llm_api_key}"})
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
