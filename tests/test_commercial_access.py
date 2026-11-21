from datetime import datetime, timedelta, timezone
import pytest
from app.db import SessionLocal
from app.commercial.access import (
    CommercialUser, CommercialSubscription, AccessDenied,
    register_pending, require_commercial_access,
)


def test_registration_never_auto_verifies():
    with SessionLocal() as db:
        profile = register_pending(db, "max:123")
        db.commit()
        assert profile.verification_status == "pending"
        with pytest.raises(AccessDenied, match="verification_required"):
            require_commercial_access(db, "max:123")


def test_unregistered_is_blocked():
    with SessionLocal() as db:
        with pytest.raises(AccessDenied, match="registration_required"):
            require_commercial_access(db, "max:404")


def test_max_identity_required():
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            register_pending(db, "local:123")


def test_access_requires_active_entitlement():
    with SessionLocal() as db:
        profile = register_pending(db, "max:456")
        profile.verification_status = "verified"  # fixture simulates trusted verification
        profile.verified_at = datetime.now(timezone.utc)
        profile.account_status = "active"
        db.commit()
        with pytest.raises(AccessDenied, match="subscription_required"):
            require_commercial_access(db, "max:456")
        db.add(CommercialSubscription(owner_id="max:456", plan="free", status="active"))
        db.commit()
        assert require_commercial_access(db, "max:456") == "free"


def test_expired_or_suspended_is_blocked():
    with SessionLocal() as db:
        profile = register_pending(db, "max:789")
        profile.verification_status = "verified"
        profile.verified_at = datetime.now(timezone.utc)
        profile.account_status = "active"
        db.add(CommercialSubscription(
            owner_id="max:789", plan="standard", status="active",
            ends_at=datetime.now(timezone.utc) - timedelta(days=1)
        ))
        db.commit()
        with pytest.raises(AccessDenied, match="subscription_expired"):
            require_commercial_access(db, "max:789")
        db.get(CommercialUser, "max:789").account_status = "suspended"
        db.commit()
        with pytest.raises(AccessDenied, match="account_inactive"):
            require_commercial_access(db, "max:789")
