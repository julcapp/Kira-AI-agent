from datetime import datetime, timezone
import pytest
from app.db import SessionLocal
from app.commercial.access import CommercialSubscription, register_pending, AccessDenied, require_commercial_access
from app.commercial.user_management import manage_user, UserManagementEvent, ManagementDenied


def setup_user(db, uid="max:123"):
    user = register_pending(db, uid)
    user.verification_status = "verified"
    user.verified_at = datetime.now(timezone.utc)
    user.account_status = "active"
    db.add(CommercialSubscription(owner_id=uid, status="active", plan="free"))
    db.commit()


def action(db, name, reason="Внутренняя проверка по обращению"):
    return manage_user(
        db, owner_id="max:123", actor_id="staff:1", actor_role="admin",
        action=name, reason_code="manual_review", reason_text=reason
    )


def test_suspend_and_restore_audited():
    with SessionLocal() as db:
        setup_user(db)
        action(db, "suspend")
        db.commit()
        with pytest.raises(AccessDenied, match="account_inactive"):
            require_commercial_access(db, "max:123")
        action(db, "restore")
        db.commit()
        assert require_commercial_access(db, "max:123") == "free"
        assert db.query(UserManagementEvent).count() == 2


def test_block_and_deletion_request_are_non_destructive():
    with SessionLocal() as db:
        setup_user(db)
        action(db, "block")
        db.commit()
        with pytest.raises(AccessDenied):
            require_commercial_access(db, "max:123")
        ev = action(db, "request_delete")
        db.commit()
        assert ev.resulting_status == "deletion_pending"
        assert db.query(CommercialSubscription).count() == 1
        with pytest.raises(AccessDenied):
            require_commercial_access(db, "max:123")


def test_missing_reason_rejected():
    with SessionLocal() as db:
        setup_user(db)
        with pytest.raises(ValueError):
            action(db, "suspend", " ")


def test_role_restrictions():
    with SessionLocal() as db:
        setup_user(db)
        with pytest.raises(ManagementDenied, match="insufficient_privileges"):
            manage_user(
                db, owner_id="max:123", actor_id="staff:2",
                actor_role="support_manager", action="block",
                reason_code="manual_review", reason_text="Обнаружен риск злоупотребления"
            )


def test_unknown_tenant_or_state_denied():
    with SessionLocal() as db:
        setup_user(db)
        action(db, "suspend")
        db.commit()
        with pytest.raises(ManagementDenied, match="invalid_state_transition"):
            action(db, "suspend")


def test_no_audit_on_rollback():
    with SessionLocal() as db:
        setup_user(db)
        action(db, "block")
        db.rollback()
        assert db.query(UserManagementEvent).count() == 0
        assert require_commercial_access(db, "max:123") == "free"
