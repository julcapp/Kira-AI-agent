"""TTS adapter. Never log the API key or synthesized audio."""
import httpx
from ..config import settings

class TTSUnavailable(RuntimeError):
    pass

async def synthesize_mp3(text: str) -> bytes:
    if not settings.tts_enabled or not settings.tts_api_key:
        raise TTSUnavailable("TTS is not configured")
    # Large replies should not consume excessive credits or exceed provider limits.
    spoken = text[:3200]
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(
                settings.tts_base_url.rstrip("/") + "/audio/speech",
                headers={"Authorization": f"Bearer {settings.tts_api_key}"},
                json={"model": settings.tts_model, "voice": settings.tts_voice,
                      "input": spoken, "response_format": "mp3"},
            )
            res.raise_for_status()
            if not res.content or len(res.content) > 10_000_000:
                raise TTSUnavailable("Invalid audio size")
            return res.content
    except httpx.HTTPError as exc:
        raise TTSUnavailable("TTS request failed") from exc
