"""Offline provisioning of knowledge memberships by an infrastructure administrator.

Run only in a trusted shell with DATABASE_URL configured; never expose as HTTP.
Example: python -m app.knowledge.provision --tenant company-a --owner max:42 --role owner --confirm
"""
import argparse
from sqlalchemy.exc import IntegrityError
from ..db import SessionLocal
from .models import TenantMembership


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tenant", required=True)
    p.add_argument("--owner", required=True, help="Verified identity, e.g. max:42")
    p.add_argument("--role", required=True, choices=("owner", "editor", "viewer"))
    p.add_argument("--confirm", action="store_true", help="Explicitly enable DB write")
    args = p.parse_args()
    if not args.confirm:
        p.error("Supply --confirm for any database change")
    if not args.owner.startswith("max:") or not args.owner[4:].isdigit():
        p.error("Expected verified MAX identity max:<numeric_id>")
    with SessionLocal() as db:
        if db.get(TenantMembership, (args.tenant, args.owner)) is not None:
            p.error("Membership already exists; manual review required for role changes")
        db.add(TenantMembership(tenant_id=args.tenant, owner_id=args.owner, role=args.role))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            p.error("Membership conflict")
    print("Membership created; no agent permissions or public endpoints changed.")


if __name__ == "__main__":
    main()
