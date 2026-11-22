# «Ваш Финэксперт» — Documents MVP (feature branch)
Only a **non-production library prototype**. Contains an encrypted, UUID-linked object vault and tests based on synthetic data. It is NOT an upload endpoint, NOT a completed anonymizer, and does NOT permit transmission of any file to an external model. Do not feed it real financial documents until access management, encrypted backups, key management, authorized deletion, antivirus, content sanitization verification, 1C parsers, and security review have been implemented.

Run: `pip install -r requirements.txt && pytest tests/test_finexpert_document_vault.py -q`.
Integration requires per-company authorization with server-side verified identities; current MAX owner auth is NOT a company/tenant authorization model.
In particular, `store_sanitized` expects already-cleaned/validated bytes: it does **not** remove sensitive data itself.
Approved UX: «Мои документы»: originals, sanitized copies, analysis results; accounting wizard has fifth option «Комплексная проверка — всё перечисленное выше». Full UI and upload API remain a next task.
No live service, default branch, or deployment should be changed before review.
