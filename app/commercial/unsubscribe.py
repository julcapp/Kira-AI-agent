"""Voluntary unsubscribe and safe return-to-service workflow.

This service does not perform identity verification, payments, or legal deletion.
Callers must authenticate MAX user identity on the server.
"""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, Session
from ..db import Base
from .access import CommercialUser, CommercialSubscription

class UnsubscribeEvent(Base):
    __tablename__ = "commercial_unsubscribe_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("commercial_users.owner_id"), index=True
    )
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, default="not_provided")
    happened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

class UnsubscribeDenied(Exception):
    pass


def unsubscribe(db: Session, owner_id: str, *, reason_code: str = "not_provided") -> UnsubscribeEvent:
    """Opt out, halt entitlement, record event. Commit atomically at caller.

    Cancellation at billing provider must be performed by an outbox worker; until
    it succeeds, do not claim that future charges have actually stopped.
    """
    if not reason_code or len(reason_code) > 64:
        raise ValueError("Invalid reason code")
    user = db.query(CommercialUser).filter(
        CommercialUser.owner_id == owner_id,
        CommercialUser.tenant_id == "public",
    ).with_for_update().one_or_none()
    if user is None:
        raise UnsubscribeDenied("account_not_found")
    if user.account_status in ("blocked", "deletion_pending"):
        raise UnsubscribeDenied("cannot_unsubscribe_from_current_state")
    if user.account_status == "unsubscribed":
        raise UnsubscribeDenied("already_unsubscribed")
    user.account_status = "unsubscribed"
    subscription = db.get(CommercialSubscription, owner_id)
    if subscription:
        subscription.status = "inactive"
    event = UnsubscribeEvent(owner_id=owner_id, action="unsubscribe", reason_code=reason_code)
    db.add(event)
    db.flush()
    return event


def request_return(db: Session, owner_id: str) -> UnsubscribeEvent:
    """Record return intent; require trusted re-verification before reactivation.

    Never reactivate an entitlement or grant a new free quota automatically.
    """
    user = db.query(CommercialUser).filter(
        CommercialUser.owner_id == owner_id,
        CommercialUser.tenant_id == "public",
    ).with_for_update().one_or_none()
    if user is None:
        raise UnsubscribeDenied("account_not_found")
    if user.account_status != "unsubscribed":
        raise UnsubscribeDenied("return_not_allowed")
    user.account_status = "pending"
    user.verification_status = "pending"
    user.verified_at = None
    event = UnsubscribeEvent(owner_id=owner_id, action="return_requested")
    db.add(event)
    db.flush()
    return event
