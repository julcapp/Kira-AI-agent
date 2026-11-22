from dataclasses import dataclass
from .legal_rules import LEGAL_SYSTEM_PROMPT
from .specialist_rules import ACCOUNTANT_PROMPT, REWRITER_PROMPT, PROGRAMMER_PROMPT, CODE_REVIEW_PROMPT, AD_WRITER_PROMPT

@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    description: str
    system: str

AGENTS = {
    "competitors": Agent("competitors", "Аналитик конкурентов", "Сравнение конкурентов", "Анализируй конкурентов по предоставленным данным. Не выдумывай проверенные цены, ссылки или метрики. Отделяй факты от гипотез."),
    "vk": Agent("vk", "VK SMM", "Контент-план и черновики", "Создавай контент-планы и черновики постов VK. Публикация только после ручного подтверждения. Не утверждай, что публикация состоялась."),
    "lawyer": Agent("lawyer", "Юрист", "Договоры, претензии, судебные документы и правовой анализ", LEGAL_SYSTEM_PROMPT),
    "developer": Agent("developer", "IT-разработчик", "Код и архитектура", PROGRAMMER_PROMPT),
    "code_review": Agent("code_review", "Ревьюер кода", "Поиск и исправление ошибок", CODE_REVIEW_PROMPT),
    "accountant": Agent("accountant", "Бухгалтер", "Бухгалтерский и управленческий анализ", ACCOUNTANT_PROMPT),
    "rewriter": Agent("rewriter", "Рерайтер", "Редактура и улучшение текстов", REWRITER_PROMPT),
    "ad_writer": Agent("ad_writer", "Специалист по объявлениям", "Рекламные тексты и объявления", AD_WRITER_PROMPT),
    "sales": Agent("sales", "Продавец", "CRM и предложения", "Готовь скрипты продаж, КП, шаблоны сообщений. Не отправляй сообщения клиентам самостоятельно."),
    "tutor": Agent("tutor", "Репетитор", "Ученики и тренировка преподавателя", "Можешь обучать ученика и тренировать преподавателя. Определи режим из запроса; задавай вопросы по одному; давай объяснения и обратную связь."),
}
ALIASES = {
    "аналитик": "competitors", "конкурент": "competitors",
    "вк": "vk", "vk": "vk", "смм": "vk", "пост": "vk",
    "юрист": "lawyer", "договор": "lawyer",
    "бухгалтер": "accountant", "осв": "accountant",
    "рерайт": "rewriter", "перепиши текст": "rewriter",
    "ревью кода": "code_review", "отладк": "code_review",
    "объявлени": "ad_writer",
    "айти": "developer", "разработчик": "developer", "код": "developer", "сайт": "developer",
    "продавец": "sales", "продаж": "sales", "клиент": "sales",
    "репетитор": "tutor", "ученик": "tutor", "урок": "tutor", "преподавател": "tutor",
}
def choose_agent(message: str) -> str:
    lowered = message.lower()
    for token, agent in ALIASES.items():
        if token in lowered:
            return agent
    return "kiryusha"
