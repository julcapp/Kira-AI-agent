# Persistent Skill Library & Brand Passport API — Stage 2

This feature is a **draft**, stacked on PR #4 (in-memory skill/brand models). No production rollout or merge is authorized.

## Storage
The additive Alembic migration `20261122_01` creates:
- `knowledge_memberships` (tenant, authenticated MAX identity, role)
- `knowledge_skill_versions` (immutable payload by tenant/slug/version; status transition controlled)
- `knowledge_agent_grants` (tenant-bound skill-to-agent permissions)
- `knowledge_brand_revisions` (immutable brand snapshots with provenance and sensitivity)
- `knowledge_audit` (actor, tenant, action, key, time)

All tables support PostgreSQL through SQLAlchemy, and SQLite for development/tests. The legacy MVP tables remain outside this migration. Existing deployment tables must be backed up and examined before the migration.

## Authentication & access
Knowledge API uses **signed MAX initData** (`X-MAX-Init-Data`) plus membership stored server-side. The URL's `tenant_id` is never treated as authorization. Memberships cannot be created or updated via web API.
- owner: create, approve, publish, grant, read protected context
- editor: create drafts and submit skills for testing; draft brand facts are never self-approved
- viewer: read permitted catalogue and approved public/internal brand context

Bootstrap a member **only on a trusted host after backups and authentication review**:
`python -m app.knowledge.provision --tenant company-a --owner max:42 --role owner --confirm`
No membership is provisioned automatically. An infrastructure administrator must verify organization ownership and MAX identity first.

## API examples
- `GET /api/mini/knowledge/{tenant_id}/skills`
- `POST /api/mini/knowledge/{tenant_id}/skills`
- `POST /api/mini/knowledge/{tenant_id}/skills/{slug}/{version}/advance`
- `POST /api/mini/knowledge/{tenant_id}/skills/{slug}/{version}/grants`
- `GET /api/mini/knowledge/{tenant_id}/agents/{agent_key}/skills`
- `POST /api/mini/knowledge/{tenant_id}/brands`
- `GET /api/mini/knowledge/{tenant_id}/brands/{brand_id}/context`

The `advance` endpoint implements draft -> testing -> approved -> published, but **does not** automatically run or verify test suites. Do not use this endpoint for real publication until the approval workflow is linked to mandatory test results and an independent publication gate.

## Validation and rollout
In a **disposable/test database** (not production):
`alembic upgrade head`
`pytest -q`
The GitHub Actions workflow tests both. Do not run schema migrations on an active production database without backup, restore drill, migration diff review, a maintenance window and explicit approval.

## Remaining blockers before production
- External identity & registration lifecycle; paid subscriptions and per-tenant organization membership administration;
- Complete RBAC/ABAC and source-sensitive context policy, encrypted secret store, and audit retention;
- Disable or isolate legacy development `/api/chat` key on public deployments;
- No automatic skill execution; implement safe runner, tool grants, approval queue, sandbox, rollback and quotas;
- Test-run evidence before publishing; editor-to-owner review, tenant ownership proof;
- Database migration rehearsals with PostgreSQL, concurrent write tests and actual integration against MAX;
- UI for CRM, editor and brand passport, backups, monitoring, rate limiting and tests for abuse.
