"""Commercial access policy; no MAX credential or OTP verification is performed here.

Only a trusted, separately audited verifier may set verification_status='verified'.
"""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from ..db import Base

class CommercialUser(Base):
    __tablename__ = "commercial_users"
    owner_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, default="public")
    verification_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    account_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class CommercialSubscription(Base):
    __tablename__ = "commercial_subscriptions"
    owner_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("commercial_users.owner_id"), primary_key=True
    )
    plan: Mapped[str] = mapped_column(String(24), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="inactive")
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessDenied(Exception):
    """Commercial request is not authorized."""


def register_pending(db: Session, owner: str) -> CommercialUser:
    """Create a pending profile; MUST NOT grant access or verify a phone."""
    if not owner.startswith("max:") or not owner[4:].isdigit():
        raise ValueError("Commercial registration requires authenticated MAX identity")
    profile = db.get(CommercialUser, owner)
    if profile is None:
        profile = CommercialUser(owner_id=owner)
        db.add(profile)
        db.flush()
    return profile


def require_commercial_access(db: Session, owner: str, now: datetime | None = None) -> str:
    """Fail closed unless identity and paid/free entitlement are both active."""
    now = now or datetime.now(timezone.utc)
    profile = db.get(CommercialUser, owner)
    if profile is None:
        raise AccessDenied("registration_required")
    if profile.tenant_id != "public":
        raise AccessDenied("tenant_not_authorized")
    if profile.verification_status != "verified" or profile.verified_at is None:
        raise AccessDenied("verification_required")
    if profile.account_status != "active":
        raise AccessDenied("account_inactive")
    subscription = db.get(CommercialSubscription, owner)
    if subscription is None or subscription.status != "active":
        raise AccessDenied("subscription_required")
    if subscription.ends_at is not None:
        expires = subscription.ends_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= now:
            raise AccessDenied("subscription_expired")
    if subscription.plan not in ("free", "standard", "professional"):
        raise AccessDenied("plan_invalid")
    return subscription.plan
