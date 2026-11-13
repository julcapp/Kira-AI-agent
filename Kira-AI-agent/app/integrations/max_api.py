import httpx
from ..config import settings

MAX_API_BASE = "https://platform-api2.max.ru"

async def send_max_message(user_id: int, text: str) -> None:
    if not (settings.max_enabled and settings.max_bot_token):
        raise RuntimeError("MAX integration disabled")
    async with httpx.AsyncClient(timeout=15) as client:
        # MAX text limit is 4000 chars. Split long replies into chunks.
        for start in range(0, len(text), 3500):
            response = await client.post(
                f"{MAX_API_BASE}/messages",
                params={"user_id": user_id},
                headers={"Authorization": settings.max_bot_token},
                json={"text": text[start:start+3500]},
            )
            response.raise_for_status()

def extract_message_text(body: dict) -> str:
    """Use MAX supplied audio transcript when a text message is absent."""
    text = body.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    for attachment in body.get("attachments") or []:
        if not isinstance(attachment, dict) or attachment.get("type") != "audio":
            continue
        attachment_payload = attachment.get("payload") or {}
        transcript = attachment_payload.get("transcription")
        if isinstance(transcript, str) and transcript.strip():
            return transcript.strip()
    if any(isinstance(a, dict) and a.get("type") == "audio"
           for a in (body.get("attachments") or [])):
        return "/voice_unavailable"
    return ""


def parse_incoming(payload: dict) -> tuple[int, str, str] | None:
    if payload.get("update_type") != "message_created":
        return None
    message = payload.get("message") or {}
    sender = message.get("sender") or {}
    body = message.get("body") or {}
    user_id = sender.get("user_id")
    text = extract_message_text(body)
    event_id = message.get("body", {}).get("mid")
    if sender.get("is_bot") or not isinstance(user_id, int) or not isinstance(text, str) or not text.strip() or not event_id:
        return None
    return user_id, text, str(event_id)


async def send_max_audio(user_id: int, mp3: bytes) -> None:
    """MAX: create upload -> multipart upload -> send audio attachment.

    MAX may need a short processing delay; retry only attachment.not.ready.
    """
    import asyncio
    if not (settings.max_enabled and settings.max_bot_token):
        raise RuntimeError("MAX integration disabled")
    headers = {"Authorization": settings.max_bot_token}
    async with httpx.AsyncClient(timeout=40, follow_redirects=False) as client:
        ticket = await client.post(
            f"{MAX_API_BASE}/uploads",
            params={"type": "audio"}, headers=headers,
        )
        ticket.raise_for_status()
        data = ticket.json()
        upload_url, token = data["url"], data["token"]
        # Only upload to the MAX CDN endpoint, never an arbitrary URL.
        from urllib.parse import urlparse
        parsed = urlparse(upload_url)
        if parsed.scheme != "https" or parsed.hostname not in {"omu.okcdn.ru"}:
            raise ValueError("Untrusted MAX upload host")
        uploaded = await client.post(
            upload_url,
            files={"data": ("kiryusha.mp3", mp3, "audio/mpeg")},
        )
        uploaded.raise_for_status()
        for attempt in range(4):
            response = await client.post(
                f"{MAX_API_BASE}/messages",
                params={"user_id": user_id},
                headers=headers,
                json={"attachments": [{"type": "audio", "payload": {"token": token}}]},
            )
            if response.is_success:
                return
            # MAX documents that media processing may continue after upload.
            if response.status_code in (400, 409) and "attachment.not.ready" in response.text and attempt < 3:
                await asyncio.sleep(2 ** attempt)
                continue
            response.raise_for_status()
