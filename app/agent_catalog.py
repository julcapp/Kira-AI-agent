"""CRM-managed agent catalog: isolated prototype, not a live authorization gateway.

The catalog manages presentation and routing metadata only. Actual permissions,
subscription entitlements and organization grants MUST be checked separately
by the backend before invoking tools or accessing data.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Iterable
import re

KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
ROUTES = {"lawyer", "accountant", "sales", "vk", "competitors", "developer", "tutor"}
ROOTS = (
    ("lawyer", "⚖️ Юрист", "lawyer"),
    ("finance", "💰 Ваш Финэксперт", "accountant"),
    ("manager", "🤝 Менеджер", "sales"),
    ("marketing", "📣 Маркетолог", "vk"),
    ("developer", "💻 IT-разработчик", "developer"),
    ("education", "🎓 Преподаватель", "tutor"),
)

@dataclass(frozen=True)
class CatalogEntry:
    key: str
    title: str
    parent_key: str | None = None
    route: str | None = None
    enabled: bool = True
    order: int = 0
    required_role: str | None = None
    required_plan: str | None = None


def initial_entries() -> list[CatalogEntry]:
    result = [CatalogEntry(key, title, route=route, order=i) for i, (key, title, route) in enumerate(ROOTS)]
    submenus = {
        "lawyer": [("contracts","Договоры","lawyer"),("debt","Претензии и взыскание","lawyer")],
        "finance": [("accounting","Бухгалтерский учёт","accountant"),
                    ("navigation","Персональный финансовый навигатор","accountant")],
        "manager": [("crm","Клиенты и CRM","sales"),("sales","Продажи","sales")],
        "marketing": [("vk","VK и соцсети","vk"),("ads","Реклама","vk"),("competitors","Конкуренты","competitors")],
        "developer": [("code","Программирование","developer"),("web","Верстка сайтов","developer")],
        "education": [("courses","Обучение","tutor"),("tutor","Репетитор","tutor")],
    }
    for parent, children in submenus.items():
        for index, (key,title,route) in enumerate(children):
            result.append(CatalogEntry(key,title,parent,route=route,order=index))
    return result


class Catalog:
    def __init__(self, entries: Iterable[CatalogEntry]):
        self.entries = list(entries)
        self._validate()

    def _validate(self):
        roots = [e for e in self.entries if e.parent_key is None]
        if [e.key for e in sorted(roots,key=lambda x:x.order)] != [item[0] for item in ROOTS]:
            raise ValueError("Exactly six fixed root sections are required")
        seen = set()
        for e in self.entries:
            if not KEY.fullmatch(e.key) or not e.title.strip() or len(e.title)>90:
                raise ValueError("Invalid catalog entry")
            identifier=(e.parent_key,e.key)
            if identifier in seen:
                raise ValueError("Duplicate item in one menu")
            seen.add(identifier)
            if e.route is not None and e.route not in ROUTES:
                raise ValueError("Unregistered route")
        for entry in self.entries:
            if entry.parent_key is not None:
                matches=[p for p in self.entries if p.key == entry.parent_key]
                if len(matches)!=1:
                    raise ValueError("Unknown or ambiguous parent")
        by_key={e.key:e for e in self.entries}
        for e in self.entries:
            visited=set()
            node=e
            while node.parent_key:
                if node.key in visited:
                    raise ValueError("Catalog cycle")
                visited.add(node.key)
                node=by_key[node.parent_key]

    def children(self, parent_key: str | None):
        if parent_key is not None and parent_key not in {e.key for e in self.entries}:
            raise ValueError("Unknown category")
        return sorted((e for e in self.entries if e.parent_key == parent_key and e.enabled),
                      key=lambda x:(x.order,x.key))

    def resolve(self, path: tuple[str,...]) -> CatalogEntry | None:
        node=None
        for key in path:
            matches=[e for e in self.children(node.key if node else None) if e.key==key]
            if not matches:
                raise ValueError("Unknown or disabled route")
            node=matches[0]
        return node

    def inline_keyboard(self, path: tuple[str,...]=()):
        self.resolve(path)
        rows=[]
        for child in self.children(path[-1] if path else None):
            payload="catalog:"+"/".join((*path,child.key))
            if len(payload.encode())>100:
                raise ValueError("Menu nesting exceeds callback capacity")
            rows.append([{"type":"callback","text":child.title,"payload":payload}])
        if path:
            rows.append([{"type":"callback","text":"⬅️ Назад",
                          "payload":"catalog:"+"/".join(path[:-1])}])
        rows.append([{"type":"callback","text":"🏠 Главное меню","payload":"catalog:"}])
        return {"type":"inline_keyboard","payload":{"buttons":rows}}

    def set_enabled(self, parent_key: str|None, key: str, enabled: bool):
        """An authorized CRM service could apply this after RBAC and audit."""
        found=False
        updated=[]
        for e in self.entries:
            if e.parent_key==parent_key and e.key==key:
                if parent_key is None and not enabled:
                    raise ValueError("Six primary sections must remain present")
                e=replace(e,enabled=enabled)
                found=True
            updated.append(e)
        if not found:
            raise ValueError("Unknown entry")
        return Catalog(updated)


def decode_callback(payload: str) -> tuple[str,...]:
    if not isinstance(payload,str) or not payload.startswith("catalog:") or len(payload)>110:
        raise ValueError("Invalid callback")
    value=payload[len("catalog:"):]
    parts=tuple(value.split("/")) if value else ()
    if any(not KEY.fullmatch(part) for part in parts):
        raise ValueError("Invalid callback route")
    return parts
