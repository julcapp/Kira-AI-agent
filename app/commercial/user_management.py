"""Commercial user lifecycle service. Never expose directly without admin auth.

Permanent erasure requires separate retention-aware worker and legal review.
"""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session
from ..db import Base
from .access import CommercialUser

VALID_ACTIONS = frozenset({"suspend", "block", "restore", "request_delete"})
ALLOWED_ROLES = {
    "suspend": frozenset({"owner", "admin", "support_manager"}),
    "block": frozenset({"owner", "admin"}),
    "restore": frozenset({"owner", "admin"}),
    "request_delete": frozenset({"owner", "admin"}),
}

class UserManagementEvent(Base):
    __tablename__ = "commercial_user_management_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(100), ForeignKey("commercial_users.owner_id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(24), nullable=False)
    resulting_status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ManagementDenied(Exception):
    pass


def manage_user(
    db: Session, *,
    owner_id: str,
    actor_id: str,
    actor_role: str,
    action: str,
    reason_code: str,
    reason_text: str,
) -> UserManagementEvent:
    """Change access state and append an audit event in one DB transaction.

    Does not commit: caller must commit atomically and ensure actor identity and
    role came from trusted, authenticated server-side RBAC, never request JSON.
    """
    if action not in VALID_ACTIONS:
        raise ValueError("Unknown account action")
    if actor_role not in ALLOWED_ROLES[action] or not actor_id.strip():
        raise ManagementDenied("insufficient_privileges")
    reason_code = reason_code.strip()
    reason_text = reason_text.strip()
    if not (2 <= len(reason_code) <= 64) or not (5 <= len(reason_text) <= 2000):
        raise ValueError("Reason code and reason text are required")
    # Row lock prevents concurrent administrators from overwriting each other.
    profile = db.query(CommercialUser).filter(
        CommercialUser.owner_id == owner_id,
        CommercialUser.tenant_id == "public",
    ).with_for_update().one_or_none()
    if profile is None:
        raise ManagementDenied("user_not_found_or_wrong_tenant")
    if owner_id == actor_id:
        raise ManagementDenied("self_management_forbidden")
    previous = profile.account_status
    transitions = {
        "suspend": {"active", "pending"},
        "block": {"active", "pending", "suspended"},
        "restore": {"blocked", "suspended"},
        "request_delete": {"active", "pending", "suspended", "blocked"},
    }
    if previous not in transitions[action]:
        raise ManagementDenied("invalid_state_transition")
    target_status = {
        "suspend": "suspended",
        "block": "blocked",
        "restore": "active" if profile.verification_status == "verified" and profile.verified_at else "pending",
        "request_delete": "deletion_pending",
    }[action]
    profile.account_status = target_status
    event = UserManagementEvent(
        owner_id=owner_id, actor_id=actor_id, actor_role=actor_role,
        action=action, previous_status=previous, resulting_status=target_status,
        reason_code=reason_code, reason_text=reason_text,
    )
    db.add(event)
    db.flush()
    return event
