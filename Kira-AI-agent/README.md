# Кирюша AI Office — MAX Mini App MVP

Один чат-бот MAX + одно мини-приложение со вкладками 6 агентов и координатора.
Репозиторий назначения: https://github.com/julcapp/Kira-AI-agent

## Возможности
- `/app` — адаптивный интерфейс мини-приложения;
- выбор агента (координатор, конкуренты, VK, юрист, IT, продажи, репетитор);
- общий диалог с backend-оркестратором (AI-модель подключается через `.env`);
- персональный список задач и идей;
- серверная проверка `WebAppData` (HMAC SHA256, срок 1 час, allowlist MAX ID);
- исходный MAX-бот, голосовые команды и голосовые режимы из Voice v2 сохранены.

В MVP нет реальных интеграций VK/CRM, автоматического парсинга конкурентов и выполнения программ.
Голос через чат MAX; в самом WebApp микрофон не реализован.

## Локальный запуск

```bash
cp .env.example .env
# обязательно заменить APP_API_KEY и при публичном запуске настроить MAX_ALLOWED_USER_IDS
docker compose up -d --build
# открыть http://127.0.0.1:8000/app
```

В браузере без MAX виден интерфейс-предпросмотр, API данных недоступно без валидной авторизации.
Для тестов установите зависимости локально: `pip install -r requirements.txt && pytest -q`.
Фронтенд без Node/npm, статические файлы отдаются FastAPI.

## Подключение MAX после модерации

1. Развернуть приложение за HTTPS (reverse proxy Caddy/nginx); например `https://kiryusha.example.ru/app`.
2. В `.env`: `MAX_ENABLED=true`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `MAX_ALLOWED_USER_IDS`.
3. Зарегистрировать webhook `https://kiryusha.example.ru/webhooks/max` на стороне MAX.
4. В MAX для партнёров открыть **Чат-боты → Кирюша → Настройки → Мини-приложение**; ввести **полный HTTPS URL** `https://kiryusha.example.ru/app`; выбрать кнопку «Открыть» и сохранить.
5. Проверить мини-приложение внутри MAX и сообщения бота.

Нельзя использовать ссылку github.com как URL приложения: это репозиторий исходников, а MAX нужен адрес *работающего HTTPS веб-сервиса*. GitHub Pages для этого MVP недостаточно: здесь требуется серверная проверка подписи и база данных.

## Схема
- `app/main.py`: HTTP, MAX webhook, API Mini App
- `app/miniapp_auth.py`: защита API Mini App
- `app/static/`: интерфейс
- `app/core/orchestrator.py`: маршрутизатор команд
- `app/agents/registry.py`: 6 агентов
- `app/db.py`: задачи, идеи, предпочтения
- `app/integrations/`: API MAX и TTS
- `tests/`: локальные проверки

## Безопасность и доработки для production
- Настроить TLS и приватные секреты только в `.env`, не коммитить `.env`.
- Включить список разрешённых пользователей MAX и ограничение скорости API.
- Перед production обновить SQLite на PostgreSQL, добавить миграции Alembic, очередь заданий/outbox и резервное копирование.
- Вынести задачи по расписанию в отдельный worker (не создавать несколько планировщиков).
- Действия агентов с публикациями и финансово/юридически значимыми последствиями — только после подтверждения.
- Голосовые ответы доступны через бот, а не WebApp.
- При открытии только в обычном браузере WebApp не предоставляет авторизацию: требуется запуск из MAX.

## GitHub — первый коммит
```bash
git init
git branch -M main
git add .
git commit -m "feat: MAX mini app with six agents and secure WebApp auth"
git remote add origin https://github.com/julcapp/Kira-AI-agent.git
git push -u origin main
```
Вход в GitHub выполняется отдельно (SSH-ключ или Git Credential Manager); секреты в репозиторий не добавляйте.

Официальные документы:
- https://dev.max.ru/docs/webapps/introduction
- https://dev.max.ru/docs/webapps/validation
- https://dev.max.ru/docs/webapps/bridge
