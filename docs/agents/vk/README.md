# VK Social AI — У Тимоши — pilot v0.1

## Scope
- First tenant: `utimoshi`, first channel: VK.
- Existing MAX/FastAPI deployment in `app/` stays unchanged.
- MCP Gateway starts only by explicit local command; **not** included in production compose.
- Initial MCP tools are offline read-only diagnostics and content-plan preview.
- **VK access, production server deployment, published posts, ads and CRM integration are NOT implemented yet.**

## Repository audit (2026-11-21)
- Main app: FastAPI in `app/main.py`, MAX webhook + Mini App.
- Orchestration: `app/core/orchestrator.py`, agent registry: `app/agents/registry.py`.
- Persistent data: `app/db.py`, scheduler: `app/scheduler.py`.
- `docker-compose.yml` runs one `api` worker on local port 8000.
- Existing README notes VK/CRM integrations as not yet implemented.
- Avoid coupling MCP lifecycle to the embedded scheduler.

## Test locally
```bash
python -m unittest discover -s services/social_ai/tests -v
python -m pip install -r services/social_ai/requirements.txt
python -m services.social_ai.mcp_server
```
The last command uses STDIO MCP protocol: use an MCP client; it will not display a web UI. Do not put human-readable logs on STDOUT.

## Rollout gates
1. Security/code review + test suite green.
2. Verify VK official API scope, token storage and applicable platform restrictions.
3. Add VK read-only adapter; no hard-coded access tokens or scraped credentials.
4. Introduce authenticated gateway identity, tenant isolation and audit log.
5. Confirm callback validation/idempotency before accepting webhooks.
6. Add immutable approvals before enabling posting, messages or advertising.
7. Separate deployment in dedicated staging service; change production only with explicit approval and rollback plan.

## Decisions
- ADR-001: Own MCP gateway; official VK API as provider; inspect third-party MCP code as reference only.
- ADR-002: Tenant isolation and allowlisted tools enforced in backend, never trusted to AI prompts.
- ADR-003: First pilot is offline read-only, publication disabled.
