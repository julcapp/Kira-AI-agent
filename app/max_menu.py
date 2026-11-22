"""MAX inline hierarchy prototype. Pure data and validation, NO live webhook changes.

Callback payloads contain only bounded routing keys; no user or company secrets.
Authorization to use a specialist or nested tool must be checked server-side.
"""
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class MenuItem:
    key: str
    title: str
    children: tuple = ()
    agent: str | None = None

CATALOG = (
    MenuItem("lawyer", "⚖️ Юрист", (
        MenuItem("contracts", "Договоры", agent="lawyer"),
        MenuItem("debt", "Претензии и взыскание", agent="lawyer"),
        MenuItem("review", "Правовой анализ", agent="lawyer"),
    )),
    MenuItem("finexpert", "💰 Ваш Финэксперт", (
        MenuItem("accounting", "Бухгалтерский учёт", agent="accountant"),
        MenuItem("financial_navigation", "Персональный финансовый навигатор", agent="accountant"),
        MenuItem("documents", "Мои документы", agent="accountant"),
    )),
    MenuItem("manager", "🤝 Менеджер", (
        MenuItem("crm", "CRM и клиенты", agent="sales"),
        MenuItem("sales", "Продажи", agent="sales"),
        MenuItem("tasks", "Задачи", agent="sales"),
    )),
    MenuItem("marketing", "📣 Маркетолог", (
        MenuItem("vk", "VK и социальные сети", agent="vk"),
        MenuItem("ads", "Рекламные кампании", agent="vk"),
        MenuItem("competitors", "Анализ конкурентов", agent="competitors"),
    )),
    MenuItem("developer", "💻 IT-разработчик", (
        MenuItem("code", "Программирование", agent="developer"),
        MenuItem("web", "Верстка сайтов", agent="developer"),
        MenuItem("tests", "Тестирование", agent="developer"),
        MenuItem("infra", "Инфраструктура", agent="developer"),
    )),
    MenuItem("teacher", "🎓 Преподаватель", (
        MenuItem("courses", "Создание курсов", agent="tutor"),
        MenuItem("tutor", "Репетитор", agent="tutor"),
    )),
)


def find(path: tuple[str, ...]):
    items = CATALOG
    current = None
    for key in path:
        current = next((item for item in items if item.key == key), None)
        if current is None:
            raise ValueError("Unknown menu path")
        items = current.children
    return current


def button(label: str, payload: str) -> dict:
    if not payload or len(payload.encode()) > 1024:
        raise ValueError("Callback payload too long")
    return {"type": "callback", "text": label, "payload": payload}


def keyboard(path: tuple[str, ...] = ()) -> dict:
    node = find(path) if path else None
    if node and not node.children:
        raise ValueError("Leaf is not a menu")
    items = node.children if node else CATALOG
    rows = [[button(item.title, "menu:" + "/".join((*path, item.key)))] for item in items]
    if path:
        rows.append([button("⬅️ Назад", "menu:" + "/".join(path[:-1]))])
    rows.append([button("🏠 Главное меню", "menu:")])
    return {"type": "inline_keyboard", "payload": {"buttons": rows}}


def resolve_callback(payload: str):
    """Return ('menu', path, None) or ('agent', path, agent-key).

    No arbitrary agent identifier from an untrusted callback is honored.
    """
    if not isinstance(payload, str) or len(payload) > 160 or not payload.startswith("menu:"):
        raise ValueError("Unsupported callback")
    raw = payload[5:]
    if raw and not re.fullmatch(r"[a-z0-9_]+(?:/[a-z0-9_]+)*", raw):
        raise ValueError("Malformed callback")
    path = tuple(raw.split("/")) if raw else ()
    if len(path) > 4:
        raise ValueError("Navigation depth exceeded")
    node = find(path) if path else None
    if node and not node.children:
        return ("agent", path, node.agent)
    return ("menu", path, None)
