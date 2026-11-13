import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, or_
from .db import SessionLocal, Record
from .config import settings
from .integrations.max_api import send_max_message

log = logging.getLogger(__name__)

async def check_reminders():
    # Single scheduler worker for MVP. For multiple replicas use a queue/atomic lease.
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        pending = db.scalars(
            select(Record).where(Record.kind == "task", Record.status == "open",
                                 Record.due_at.is_not(None), Record.delivered_at.is_(None),
                                 Record.due_at <= now).limit(20)
        ).all()
        for record in pending:
            if not settings.max_enabled:
                continue  # don't mark as delivered until MAX is connected
            if not record.owner_id.startswith("max:"):
                continue  # local test users have no MAX destination
            try:
                await send_max_message(int(record.owner_id[4:]), f"⏰ Напоминание #{record.id}: {record.title}")
                record.delivered_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                log.exception("Reminder delivery failed for record %s", record.id)
                db.rollback()

async def scheduler_loop():
    while True:
        try:
            await check_reminders()
        except Exception:
            log.exception("Reminder scheduler error")
        await asyncio.sleep(15)
