"""FinExpert prototype: encrypted immutable originals and linked sanitized versions.

Not wired to HTTP endpoints. Provision a dedicated key, storage and tenant authorization
before production. Callers MUST validate organization permissions independently.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from cryptography.fernet import Fernet


class VaultError(ValueError):
    pass


def _safe_component(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value):
        raise VaultError("Invalid tenant or organization identifier")
    return value


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentVault:
    """Prototype API: the database and files must be on non-public storage.

    A derived file NEVER replaces its original. Each artifact has its own UUID.
    This is encryption at rest, not cryptographic protection against server admins.
    """

    def __init__(self, root: str | Path, key: bytes):
        if not key:
            raise VaultError("Encryption key required")
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.cipher = Fernet(key)
        self.db_path = self.root / "index.sqlite3"
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS artifacts (
                  id TEXT PRIMARY KEY,
                  tenant TEXT NOT NULL,
                  organization TEXT NOT NULL,
                  kind TEXT NOT NULL CHECK (kind IN ('original','sanitized','result')),
                  parent_id TEXT REFERENCES artifacts(id),
                  sha256 TEXT NOT NULL,
                  object_key TEXT NOT NULL UNIQUE,
                  content_type TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  policy TEXT NOT NULL,
                  CHECK ((kind='original' AND parent_id IS NULL)
                     OR (kind!='original' AND parent_id IS NOT NULL))
                );
                CREATE INDEX IF NOT EXISTS idx_artifacts_owner
                ON artifacts(tenant, organization, created_at);
            """)

    def _db(self):
        return sqlite3.connect(self.db_path)

    def _write_once(self, object_key: str, payload: bytes) -> None:
        """Exclusive file creation prevents overwriting an original or prior version."""
        target = self.root / object_key
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(self.cipher.encrypt(payload))
                output.flush()
                os.fsync(output.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise

    def _put(self, *, tenant: str, organization: str, kind: str,
             payload: bytes, content_type: str, parent_id: str | None,
             policy: str) -> str:
        tenant = _safe_component(tenant)
        organization = _safe_component(organization)
        if not isinstance(payload, bytes) or len(payload) == 0:
            raise VaultError("A nonempty byte payload is required")
        if len(payload) > 10 * 1024 * 1024:
            raise VaultError("Prototype supports at most 10 MB")
        if kind not in {"original", "sanitized", "result"}:
            raise VaultError("Invalid artifact type")
        if kind == "original" and parent_id is not None:
            raise VaultError("Original may not have a parent")
        if kind != "original":
            if not parent_id:
                raise VaultError("Derived artifact requires parent ID")
            self._metadata(tenant, organization, parent_id)
        artifact_id = str(uuid.uuid4())
        object_key = f"{artifact_id}.encrypted"
        digest = hashlib.sha256(payload).hexdigest()
        with self._db() as db:
            self._write_once(object_key, payload)
            try:
                db.execute(
                    """INSERT INTO artifacts(id,tenant,organization,kind,parent_id,sha256,
                    object_key,content_type,created_at,policy) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (artifact_id, tenant, organization, kind, parent_id,
                     digest, object_key, content_type, _utc(), policy)
                )
                db.commit()
            except BaseException:
                (self.root / object_key).unlink(missing_ok=True)
                raise
        return artifact_id

    def _metadata(self, tenant: str, organization: str, artifact_id: str):
        with self._db() as db:
            row = db.execute(
                """SELECT id,kind,parent_id,sha256,object_key,content_type,created_at,policy
                FROM artifacts WHERE id=? AND tenant=? AND organization=?""",
                (artifact_id, _safe_component(tenant), _safe_component(organization))
            ).fetchone()
        if row is None:
            raise VaultError("Artifact not found in the authorized organization")
        return dict(zip(("id","kind","parent_id","sha256","object_key",
                         "content_type","created_at","policy"), row))

    def ingest_original(self, tenant: str, organization: str, payload: bytes,
                        content_type: str = "application/octet-stream") -> str:
        return self._put(tenant=tenant, organization=organization, kind="original",
                         payload=payload, parent_id=None, content_type=content_type, policy="immutable")

    def store_sanitized(self, tenant: str, organization: str, parent_id: str,
                        payload: bytes, policy: str = "redaction-v1") -> str:
        parent = self._metadata(tenant, organization, parent_id)
        if parent["kind"] != "original":
            raise VaultError("Sanitized copy must reference original")
        if not policy:
            raise VaultError("Sanitization policy must be recorded")
        # Caller MUST complete independent redaction verification before calling.
        return self._put(tenant=tenant, organization=organization, kind="sanitized",
                         payload=payload, parent_id=parent_id,
                         content_type="application/octet-stream", policy=policy)

    def store_result(self, tenant: str, organization: str, sanitized_id: str,
                     result: dict) -> str:
        parent = self._metadata(tenant, organization, sanitized_id)
        if parent["kind"] != "sanitized":
            raise VaultError("Results must reference a sanitized copy")
        return self._put(tenant=tenant, organization=organization, kind="result",
                         parent_id=sanitized_id,
                         payload=json.dumps(result, ensure_ascii=False).encode("utf-8"),
                         content_type="application/json", policy="analysis-v1")

    def read(self, tenant: str, organization: str, artifact_id: str) -> bytes:
        meta = self._metadata(tenant, organization, artifact_id)
        data = self.cipher.decrypt((self.root / meta["object_key"]).read_bytes())
        if hashlib.sha256(data).hexdigest() != meta["sha256"]:
            raise VaultError("Integrity check failed")
        return data

    def list_artifacts(self, tenant: str, organization: str) -> list[dict]:
        with self._db() as db:
            ids = db.execute(
                "SELECT id FROM artifacts WHERE tenant=? AND organization=? ORDER BY created_at,id",
                (_safe_component(tenant), _safe_component(organization))
            ).fetchall()
        return [self._metadata(tenant, organization, row[0]) for row in ids]
