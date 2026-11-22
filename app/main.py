import asyncio
import hmac
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import init_db, SessionLocal, InboxEvent, VoicePreference
from .core.orchestrator import handle_message
from .integrations.max_api import parse_incoming, send_max_message, send_max_audio
from .integrations.tts import synthesize_mp3
from .scheduler import scheduler_loop
from .knowledge.api import router as knowledge_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

app = FastAPI(title="Кирюша AI Office", version="0.2.0", lifespan=lifespan)
app.include_router(knowledge_router)

class ChatIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=12000)

def require_api_key(x_api_key: str = Header(default="")):
    if not hmac.compare_digest(x_api_key, settings.app_api_key):
        raise HTTPException(401, "Invalid API key")

@app.get("/health")
def health():
    return {"status": "ok", "mode": "max" if settings.max_enabled else "local"}

@app.post("/api/chat", dependencies=[Depends(require_api_key)])
async def chat(data: ChatIn):
    # Development API must not impersonate MAX users.
    if data.user_id.startswith("max:"):
        raise HTTPException(403, "MAX user IDs are reserved for webhook")
    with SessionLocal() as db:
        return {"reply": await handle_message(db, "local:"+data.user_id, data.message)}

@app.post("/webhooks/max")
async def max_webhook(request: Request, x_max_bot_api_secret: str = Header(default="")):
    if not settings.max_enabled or not settings.max_bot_token or not settings.max_webhook_secret:
        raise HTTPException(503, "MAX integration not configured")
    if not hmac.compare_digest(x_max_bot_api_secret, settings.max_webhook_secret):
        raise HTTPException(403, "Invalid MAX webhook secret")
    payload = await request.json()
    parsed = parse_incoming(payload)
    if parsed is None:
        return {"ok": True, "ignored": True}
    user_id, text, event_id = parsed
    if user_id not in settings.allowed_users:
        return {"ok": True, "ignored": True}
    with SessionLocal() as db:
        db.add(InboxEvent(event_id=event_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"ok": True, "duplicate": True}
        owner = f"max:{user_id}"
        reply = await handle_message(db, owner, text)
        pref = db.get(VoicePreference, owner)
        mode = pref.mode if pref else "text"

    # Non-critical delivery logic is isolated from command handling.
    # MVP caveat: durable outbox is needed before production rollout.
    if mode in ("text", "both"):
        await send_max_message(user_id, reply)
    if mode in ("audio", "both"):
        try:
            audio_bytes = await synthesize_mp3(reply)
            await send_max_audio(user_id, audio_bytes)
        except Exception:
            # In audio-only mode still deliver a meaningful reply.
            # In both-mode, the text was already delivered.
            if mode == "audio":
                await send_max_message(user_id, reply + "\\n\\n(Голосовой ответ сейчас недоступен.)")
    return {"ok": True}

# --- MAX Mini App frontend & authenticated API ---
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from .miniapp_auth import validate_init_data
from .db import Record
from .agents.registry import AGENTS

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

def web_owner(x_max_init_data: str = Header(default="")) -> str:
    return validate_init_data(x_max_init_data)

@app.get("/app", include_in_schema=False)
def miniapp():
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'self'"})

@app.get("/api/mini/agents")
def list_agents(owner: str = Depends(web_owner)):
    return {"agents": [{"key": "kiryusha", "name": "Кирюша", "description": "Координатор и планировщик"}] + [
        {"key": a.key, "name": a.name, "description": a.description}
        for a in AGENTS.values()
    ]}

@app.get("/api/mini/records")
def list_records(owner: str = Depends(web_owner)):
    with SessionLocal() as db:
        rows = db.scalars(select(Record).where(Record.owner_id == owner).order_by(Record.id.desc()).limit(100)).all()
        return {"records": [{"id": r.id, "kind": r.kind, "title": r.title, "status": r.status, "agent": r.agent,
                             "due_at": r.due_at.isoformat() if r.due_at else None} for r in rows]}

class MiniChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    agent: str = Field(default="kiryusha", max_length=40)

@app.post("/api/mini/chat")
async def mini_chat(data: MiniChatIn, owner: str = Depends(web_owner)):
    if data.agent != "kiryusha" and data.agent not in AGENTS:
        raise HTTPException(422, "Unknown agent")
    with SessionLocal() as db:
        # Explicit agent selection uses same conversation state as the MAX bot.
        from .db import Conversation
        conv = db.get(Conversation, owner)
        if conv is None:
            db.add(Conversation(owner_id=owner, selected_agent=data.agent))
        else:
            conv.selected_agent = data.agent
        db.commit()
        reply = await handle_message(db, owner, data.message)
        return {"reply": reply, "agent": data.agent}
