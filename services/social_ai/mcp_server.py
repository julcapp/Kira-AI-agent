"""Isolated MCP STDIO pilot. No VK credentials, publishing or production side effects.

Run from repository root:
    python -m pip install -r services/social_ai/requirements.txt
    python -m services.social_ai.mcp_server

The MCP tools here are intentionally read-only and operate on fixed pilot tenant.
Never expose arbitrary tenant_id or role as a caller-controlled security identity
once this service is connected to a remote gateway: replace PILOT_PRINCIPAL
with verified per-request server-side identity.
"""
from mcp.server.fastmcp import FastMCP
from .policy import Principal, PILOT_TENANT, ALLOWED_TOOLS, authorize, preview_plan

mcp = FastMCP("kiryusha-social-ai-vk-pilot")
PILOT_PRINCIPAL = Principal(tenant_id=PILOT_TENANT, role="analyst")

@mcp.tool()
def social_health() -> dict:
    """Check the isolated test MCP server; does not contact VK."""
    authorize(PILOT_PRINCIPAL, "social.health", PILOT_TENANT)
    return {"status": "ok", "mode": "offline_read_only", "tenant": PILOT_TENANT, "vk_connected": False}

@mcp.tool()
def social_capabilities() -> dict:
    """List the safe pilot capabilities; no external mutations."""
    authorize(PILOT_PRINCIPAL, "social.capabilities", PILOT_TENANT)
    return {"tenant": PILOT_TENANT, "enabled": sorted(ALLOWED_TOOLS), "publishing": False, "ads": False}

@mcp.tool()
def social_plan_preview(topic: str) -> dict:
    """Return an approval-required planning draft; no publication."""
    return preview_plan(PILOT_PRINCIPAL, PILOT_TENANT, topic)

if __name__ == "__main__":
    mcp.run(transport="stdio")
