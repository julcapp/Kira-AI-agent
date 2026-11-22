# Библиотека навыков и Паспорт бренда — архитектура и реализация фундамента

## Статус реализации
Созданы изолированные in-memory модели и реестры: `app/skills/` и `app/brands/`.
Это **не** production-модули и **не** HTTP API: нет БД, миграций, аутентификации, runtime-исполнителя, UI, интеграции с оркестратором и доступа через MAX. Запрещено подключать к публичным endpoint до авторизации, изоляции tenant и тестов.

## Library
`SkillSpec`: tenant_id, slug, version SemVer (строго X.Y.Z), title, description,
status (draft/testing/approved/published/retired), risk_level, input_schema,
output_schema, source_url, license.
`SkillGrant`: tenant_id, agent_key, slug, version.
`SkillsCatalog.register`: версия неизменна; нельзя создать дубликат.
`SkillsCatalog.grant`: только опубликованная версия, разрешение привязано к организации и агенту.
`SkillsCatalog.resolve`: выдаёт версию только при явном разрешении. Никакого auto-execute стороннего кода.

## Passport
`BrandPassport`: tenant_id, brand_id, revision, title, facts.
`BrandFact`: key, value, source, verified_at, sensitivity, approved.
`BrandRegistry.context`: только сведения текущего бренда и tenant, только утверждённые, только допустимые по уровню доступа. Проверка доступа пользователя пока НЕ реализована: allowed_levels должен передаваться будущим серверным RBAC, никогда из произвольного запроса клиента.

## Архитектурные требования следующего шага
1. PostgreSQL, миграции Alembic и ограничения UNIQUE(tenant_id, slug, version) / UNIQUE(tenant_id, brand_id, revision), внешние ключи для grants, индексы и транзакции.
2. Авторизация сотрудников и сервисных аккаунтов, RBAC/ABAC, tenant из проверенной серверной сессии; запрещено принимать tenant_id или allowed_levels от клиента как полномочия.
3. Отдельные API чтения/редактирования, workflow публикации и согласований; валидация input/output schema; immutable historical versions, отзыв доступа и аудит.
4. Утверждённые источники и проверенные версии паспорта; нельзя помещать секреты или персональные данные клиентов непосредственно в текстовые факты.
5. Подключение к оркестратору, агентам бухгалтер, маркетолог, мастер промптов, сценарист, автор статей и эксперт по вопросам только после gate-проверок.
6. Отдельные очереди выполнения, rate limits, расходы/тарифы, контроль внешних действий, тесты злоупотребления правами и утечек.

## Тестирование
Тест-кейсы в `tests/test_skill_library_brand.py`:
- нельзя назначить draft;
- нужен опубликованный skill и точный tenant+agent grant;
- нельзя повторить идентичную версию;
- только утверждённые факты доступного уровня;
- нет чтения чужого паспорта или повторного revision.
Для запуска локально: `pip install -r requirements.txt && pytest -q`.
Проверка CI в этом PR обязательна перед включением в main. Production не изменять.
