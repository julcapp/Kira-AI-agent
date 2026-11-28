# MAX: аудит официальной документации — 28.11.2026

## Первоисточники
- https://dev.max.ru/docs-api/changelog-api/
- https://dev.max.ru/docs/changelog-platform/
- https://dev.max.ru/docs-api/
- https://dev.max.ru/docs/webapps/bridge/
- https://dev.max.ru/docs/webapps/validation/
- https://dev.max.ru/docs/chatbots/bots-coding/bot-skill/
- https://dev.max.ru/docs-api/methods/POST/subscriptions

## Подтвержденные изменения платформы
- Июль: API platform-api2.max.ru и доверие к сертификату Минцифры; PATCH /me/commands; сведения о платформе/версии/устройстве в Bridge.
- Август: API и события комментариев каналов.
- Сентябрь: официальная OpenAPI YAML.
- Октябрь: MAX Messenger Agent Skill; bot_admin_permissions_changed (Webhook); PermissionsManager (Android и Web).
- Ноябрь: MAX Front App (React/Vite), STG и STG-Lite, поле code в ошибках ряда методов, удаление user из bot_added.
- Webhook: HTTPS с доверенным сертификатом; проверка секрета. Long Polling не использовать для production.

## Сверка с текущим кодом
Проверены app/integrations/max_api.py, app/static/index.html, app/static/app.js, app/scheduler.py и ранее app/miniapp_auth.py.
Новый домен уже используется. Проверка HMAC и webhook secret реализованы. В HTML отсутствует загрузка официального Bridge; CSP требует согласованного изменения. Каталог frontend задан статически и должен получать данные из авторизованного реестра backend. Обработка attachment.not.ready сейчас опирается на текст ответа; необходим структурированный разбор code с учетом схемы каждого метода. Проверить доверие TLS внутри контейнера, не отключать проверку сертификата. Реальная интеграция MAX не испытана.

## Предложенная реализация (не выполнена)
P0: проверка TLS и OpenAPI; обработка ошибок и malformed updates; проверка полного набора тестов; безопасная очередь Inbox/Outbox с атомарной фиксацией, ограниченными повторами, backoff, dead-letter, контролем дублей. Не обещать exactly-once без поддержки идемпотентности внешним API.
P1: официальный Bridge, capability detection, разрешения камеры/микрофона только по действию пользователя, резервные сценарии для неподдерживаемых клиентов; авторизованный каталог агентов; команды, callbacks, события прав администратора.
P2: официальный Agent Skill с фиксацией upstream версии/лицензии после ревью; MAX-адаптер в TimoUI; каналы и комментарии для AI-маркетинга; оценка Front App и STG без замены Python backend.
Общий backend/API/CRM и библиотека навыков сохраняются. Изменения кода интегрировать после тестирования. Пользовательские данные и секреты в публичный репозиторий не включать.
