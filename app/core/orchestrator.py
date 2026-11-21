from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..db import Record, Conversation, AuditLog, VoicePreference
from ..agents.registry import AGENTS, choose_agent
from ..llm import answer

HELP = (
    "Я Кирюша. Команды:\n"
    "/agents — список специалистов\n"
    "/agent lawyer|vk|developer|competitors|sales|tutor — выбрать специалиста\n"
    "/agent kiryusha — вернуться к координатору\n"
    "/idea текст — сохранить идею\n"
    "/task текст — создать задачу\n"
    "/remind 2026-12-01T15:00 текст — напоминание (местное время)\n"
    "/list — последние задачи и идеи\n"
    "/done ID — завершить задачу\n"
    "/help — помощь\n"
    "Голосовые сообщения с расшифровкой MAX обрабатываю как обычный текст.\n"
    "Обычный текст автоматически направлю специалисту или текущему выбранному агенту."
)

def write_log(db: Session, owner: str, agent: str, action: str, detail: str):
    db.add(AuditLog(owner_id=owner, agent=agent, action=action, detail=detail[:1500]))

def get_selected(db: Session, owner: str) -> str:
    record = db.get(Conversation, owner)
    return record.selected_agent if record else "kiryusha"

def normalize_spoken_command(message: str) -> str:
    """Recognize a few safe, deterministic Russian voice phrases.
    More complex natural-language actions require intent parsing with confirmation.
    """
    normalized = re.sub(r"\s+", " ", message.strip())
    if normalized.startswith("/"):
        return normalized
    lower = normalized.lower()
    for phrase, command in (
        ("запиши идею", "/idea"),
        ("сохрани идею", "/idea"),
        ("добавь идею", "/idea"),
        ("создай задачу", "/task"),
        ("добавь задачу", "/task"),
        ("запиши задачу", "/task"),
    ):
        if lower.startswith(phrase + " ") or lower.startswith(phrase + ":"):
            content = normalized[len(phrase):].lstrip(" :,.")
            return f"{command} {content}"
    for phrase in ("покажи мои задачи", "покажи список задач", "покажи мои идеи", "что у меня в списке"):
        if lower.rstrip("?.!") == phrase:
            return "/list"
    for name, key in (
        ("юрист", "lawyer"), ("юриста", "lawyer"),
        ("аналитик", "competitors"), ("аналитика", "competitors"),
        ("разработчик", "developer"), ("разработчика", "developer"),
        ("продавец", "sales"), ("продавца", "sales"),
        ("репетитор", "tutor"), ("репетитора", "tutor"),
        ("смм", "vk"), ("эсэмэм", "vk"),
        ("кирюша", "kiryusha"),
    ):
        if lower in (f"переключи на {name}", f"позови {name}", f"включи {name}"):
            return f"/agent {key}"
    return normalized


async def handle_message(db: Session, owner: str, message: str) -> str:
    message = normalize_spoken_command(message)
    if message == "/voice_unavailable":
        return "Получил голосовое сообщение, но MAX не прислал расшифровку. Отправь текстом или повтори голосовое. Подключение резервного распознавания речи — отдельный этап."
    if not message:
        return HELP
    lower = message.lower()
    if lower == "/upgrade" or lower.startswith("/upgrade "):
        from ..skills.prompt_upgrader import improve_prompt
        result = await improve_prompt(message[len("/upgrade"):])
        write_log(db, owner, "prompt_upgrader", "improve", "Prompt optimization requested")
        db.commit()
        return result
    if lower in ("/start", "/help"):
        return HELP
    if lower.startswith("/voice"):
        words = lower.split()
        if len(words) == 1:
            pref = db.get(VoicePreference, owner)
            return f"Режим ответа: {pref.mode if pref else 'text'}. Выбери /voice text, /voice audio или /voice both."
        if len(words) != 2 or words[1] not in ("text", "audio", "both"):
            return "Выбери /voice text, /voice audio или /voice both."
        preference = db.get(VoicePreference, owner)
        if preference is None:
            db.add(VoicePreference(owner_id=owner, mode=words[1]))
        else:
            preference.mode = words[1]
        write_log(db, owner, "kiryusha", "voice_mode", words[1])
        db.commit()
        return {"text": "Текстом", "audio": "Голосом", "both": "Текстом и голосом"}[words[1]] + " — режим сохранён."
    if lower == "/agents":
        return "\n".join(f"{a.key} — {a.name}: {a.description}" for a in AGENTS.values())
    if lower.startswith("/agent "):
        target = message.split(maxsplit=1)[1].strip().lower()
        if target != "kiryusha" and target not in AGENTS:
            return "Неизвестный агент. Список: /agents"
        session = db.get(Conversation, owner)
        if session is None:
            session = Conversation(owner_id=owner, selected_agent=target)
            db.add(session)
        else:
            session.selected_agent = target
        write_log(db, owner, target, "switch", target)
        db.commit()
        return f"Переключил на: {AGENTS[target].name if target in AGENTS else 'Кирюша'}."
    for command, kind in (("/idea ", "idea"), ("/task ", "task")):
        if lower.startswith(command):
            title = message[len(command):].strip()
            if not title or len(title) > 500:
                return "Текст должен содержать от 1 до 500 символов."
            agent = get_selected(db, owner)
            item = Record(owner_id=owner, kind=kind, title=title, agent=agent)
            db.add(item)
            db.flush()
            write_log(db, owner, agent, f"create_{kind}", str(item.id))
            db.commit()
            return f"{'Идея' if kind == 'idea' else 'Задача'} #{item.id} сохранена: {title}"
    if lower.startswith("/remind "):
        try:
            _, dt, title = message.split(maxsplit=2)
            due_local = datetime.fromisoformat(dt)
            if due_local.tzinfo is None:
                due_local = due_local.replace(tzinfo=ZoneInfo(settings.default_timezone))
            due = due_local.astimezone(timezone.utc)
            if due <= datetime.now(timezone.utc) or not (1 <= len(title) <= 500):
                return "Дата должна быть в будущем, текст — до 500 символов."
        except (ValueError, IndexError):
            return "Формат: /remind 2026-12-01T15:00 проверить договор"
        item = Record(owner_id=owner, kind="task", title=title, agent=get_selected(db, owner), due_at=due)
        db.add(item)
        db.flush()
        write_log(db, owner, item.agent, "create_reminder", str(item.id))
        db.commit()
        return f"Напоминание #{item.id} установлено: {due_local.isoformat()} — {title}"
    if lower == "/list":
        records = db.scalars(select(Record).where(Record.owner_id == owner).order_by(Record.id.desc()).limit(15)).all()
        return "\n".join(f"#{r.id} [{r.kind}/{r.status}] {r.title}" for r in records) or "Пока нет записей."
    if lower.startswith("/done "):
        try:
            record_id = int(message.split()[1])
        except (IndexError, ValueError):
            return "Формат: /done 123"
        item = db.scalar(select(Record).where(Record.id == record_id, Record.owner_id == owner, Record.kind == "task"))
        if not item:
            return "Задача не найдена."
        item.status = "done"
        write_log(db, owner, item.agent, "complete", str(item.id))
        db.commit()
        return f"Задача #{item.id} завершена."
    selected = get_selected(db, owner)
    agent_key = selected if selected != "kiryusha" else choose_agent(message)
    if agent_key == "kiryusha":
        name = "Кирюша"
        instruction = "Ты Кирюша, координатор шести AI-агентов. Разбирай запрос на подзадачи, предложи исполнителей и план. Если нужны реальные действия, попроси подтверждение. Не выдавай планы за выполненные задания."
    else:
        specialist = AGENTS[agent_key]
        name, instruction = specialist.name, specialist.system
    try:
        from ..skills.prompt_upgrader import prepare_for_agent, agent_task_message
        if settings.prompt_auto_upgrade_enabled:
            suggestion = await prepare_for_agent(message, name)
            agent_message = agent_task_message(message, suggestion)
        else:
            agent_message = message
        result = await answer(name, instruction, agent_message)
    except Exception:
        result = "AI-провайдер сейчас недоступен. Попробуй ещё раз. Команды /idea, /task и /list работают автономно."
    write_log(db, owner, agent_key, "chat", message[:500])
    db.commit()
    return result
