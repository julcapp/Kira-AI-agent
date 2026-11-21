from datetime import datetime, timezone
import pytest
from app.db import SessionLocal
from app.commercial.access import (
    CommercialSubscription, register_pending, require_commercial_access, AccessDenied,
)
from app.commercial.unsubscribe import (
    UnsubscribeEvent, UnsubscribeDenied, unsubscribe, request_return,
)


def seed(db):
    user = register_pending(db, "max:333")
    user.verification_status = "verified"
    user.verified_at = datetime.now(timezone.utc)
    user.account_status = "active"
    db.add(CommercialSubscription(owner_id="max:333", status="active", plan="standard"))
    db.commit()


def test_unsubscribe_revokes_access_retains_profile_and_audits():
    with SessionLocal() as db:
        seed(db)
        unsubscribe(db, "max:333", reason_code="no_longer_needed")
        db.commit()
        assert db.query(UnsubscribeEvent).count() == 1
        assert db.get(CommercialSubscription, "max:333").status == "inactive"
        with pytest.raises(AccessDenied, match="account_inactive"):
            require_commercial_access(db, "max:333")
        assert db.get(type(register_pending(db, "max:333")), "max:333") is not None


def test_return_requires_reverification_and_subscription():
    with SessionLocal() as db:
        seed(db)
        unsubscribe(db, "max:333")
        db.commit()
        request_return(db, "max:333")
        db.commit()
        profile = register_pending(db, "max:333")
        assert profile.account_status == "pending"
        assert profile.verification_status == "pending"
        with pytest.raises(AccessDenied, match="verification_required"):
            require_commercial_access(db, "max:333")
        assert db.get(CommercialSubscription, "max:333").status == "inactive"


def test_no_repeat_unsubscribe_or_restore_blocked():
    with SessionLocal() as db:
        seed(db)
        unsubscribe(db, "max:333")
        db.commit()
        with pytest.raises(UnsubscribeDenied, match="already_unsubscribed"):
            unsubscribe(db, "max:333")
        request_return(db, "max:333")
        with pytest.raises(UnsubscribeDenied, match="return_not_allowed"):
            request_return(db, "max:333")


def test_rollback_has_no_audit():
    with SessionLocal() as db:
        seed(db)
        unsubscribe(db, "max:333")
        db.rollback()
        assert db.query(UnsubscribeEvent).count() == 0
        assert require_commercial_access(db, "max:333") == "standard"
