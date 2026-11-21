"""Server-side policy for the read-only VK pilot; no credentials or network access."""
from dataclasses import dataclass

PILOT_TENANT = "utimoshi"
PILOT_CHANNEL = "vk"
ALLOWED_TOOLS = frozenset({"social.health", "social.capabilities", "social.plan.preview"})

@dataclass(frozen=True)
class Principal:
    tenant_id: str
    role: str

def authorize(principal: Principal, tool: str, tenant_id: str) -> None:
    if principal.tenant_id != tenant_id:
        raise PermissionError("Cross-tenant access denied")
    if principal.role not in {"owner", "admin", "analyst"}:
        raise PermissionError("Role not allowed in pilot")
    if tool not in ALLOWED_TOOLS:
        raise PermissionError("Tool not allowlisted in read-only pilot")

def preview_plan(principal: Principal, tenant_id: str, topic: str) -> dict:
    authorize(principal, "social.plan.preview", tenant_id)
    if not topic or len(topic) > 200:
        raise ValueError("topic must contain 1-200 characters")
    return {
        "tenant_id": tenant_id,
        "channel": PILOT_CHANNEL,
        "topic": topic,
        "status": "DRAFT_ONLY",
        "requires_approval": True,
        "external_action": False,
        "suggested_steps": [
            "Review public community content using authorized VK API (not connected yet)",
            "Prepare a draft and verify factual claims",
            "Request explicit human approval before any publication",
        ],
    }
