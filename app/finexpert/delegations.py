"""Prototype: director invites an accountant by phone; MAX identity must be verified externally.
Never expose bind_verified_phone / add_verified_director to public HTTP routes.
"""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
import uuid

class AccessDenied(ValueError):
    pass

def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if not 10 <= len(digits) <= 15:
        raise AccessDenied("Invalid phone")
    return "+" + digits

class DirectorAccountantRegistry:
    SCOPES = {"documents:upload", "documents:read_sanitized", "analysis:run", "reports:read"}

    def __init__(self, db_path, secret):
        if not secret or len(secret) < 32:
            raise ValueError("HMAC secret must be 32+ bytes")
        self.db_path, self.secret = str(db_path), secret
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS directors(
                   company TEXT, max_id TEXT, evidence TEXT, revoked INTEGER,
                   PRIMARY KEY(company,max_id));
                CREATE TABLE IF NOT EXISTS phone_bindings(
                   max_id TEXT PRIMARY KEY, digest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS invitations(
                   id TEXT PRIMARY KEY, company TEXT, director TEXT,
                   phone_digest TEXT, token_digest TEXT, scopes TEXT,
                   expires INTEGER, accepted_by TEXT, revoked INTEGER);
                CREATE TABLE IF NOT EXISTS grants(
                   id TEXT PRIMARY KEY, invitation TEXT UNIQUE,
                   company TEXT, accountant TEXT, scopes TEXT, revoked INTEGER);
                CREATE TABLE IF NOT EXISTS delegation_audit(
                   id TEXT PRIMARY KEY, company TEXT, actor TEXT, action TEXT,
                   subject TEXT, event_time INTEGER);
            """)

    def _db(self):
        return sqlite3.connect(self.db_path, timeout=30)

    def _digest_phone(self, value):
        return hmac.new(self.secret, normalize_phone(value).encode(), hashlib.sha256).hexdigest()

    def add_verified_director(self, company, max_id, evidence):
        # Trusted backend process only, after identity and corporate authority checks.
        if not company or not max_id.startswith("max:") or not evidence:
            raise AccessDenied("Verified director evidence required")
        with self._db() as db:
            db.execute("""INSERT INTO directors VALUES(?,?,?,NULL)
                ON CONFLICT(company,max_id) DO UPDATE SET
                evidence=excluded.evidence,revoked=NULL""", (company,max_id,evidence))

    def bind_verified_phone(self, max_id, verified_phone):
        # Only a signed MAX contact proof validator may invoke this method.
        if not max_id.startswith("max:"):
            raise AccessDenied("Authenticated MAX identity required")
        with self._db() as db:
            db.execute("""INSERT INTO phone_bindings VALUES (?,?)
                ON CONFLICT(max_id) DO UPDATE SET digest=excluded.digest""",
                (max_id,self._digest_phone(verified_phone)))

    @staticmethod
    def _require_director(db, company, director):
        exists=db.execute("""SELECT 1 FROM directors
            WHERE company=? AND max_id=? AND revoked IS NULL""",
            (company,director)).fetchone()
        if not exists:
            raise AccessDenied("Verified director required")

    @staticmethod
    def _audit(db, company, actor, action, subject, stamp):
        db.execute("INSERT INTO delegation_audit VALUES(?,?,?,?,?,?)",
                   (str(uuid.uuid4()),company,actor,action,subject,stamp))

    def invite(self, company, director, phone, scopes, *, now=None, ttl=86400):
        if not scopes or not set(scopes)<=self.SCOPES or not 0<ttl<=604800:
            raise AccessDenied("Invalid scopes or expiry")
        stamp=int(time.time() if now is None else now)
        invitation_id, token = str(uuid.uuid4()), secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_director(db,company,director)
            db.execute("INSERT INTO invitations VALUES(?,?,?,?,?,?,?,NULL,NULL)",
                (invitation_id,company,director,self._digest_phone(phone),
                hashlib.sha256(token.encode()).hexdigest(),
                ",".join(sorted(scopes)),stamp+ttl))
            self._audit(db,company,director,"invite",invitation_id,stamp)
        return invitation_id,token

    def accept(self, invitation_id, token, accountant, *, now=None):
        stamp=int(time.time() if now is None else now)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("""SELECT company,director,phone_digest,token_digest,
                scopes,expires,accepted_by,revoked FROM invitations WHERE id=?""",
                (invitation_id,)).fetchone()
            if not row:
                raise AccessDenied("Invitation missing")
            company,director,phone_digest,token_digest,scopes,expires,accepted,revoked=row
            binding=db.execute("SELECT digest FROM phone_bindings WHERE max_id=?",
                               (accountant,)).fetchone()
            if revoked is not None or accepted is not None or stamp>=expires or accountant==director:
                raise AccessDenied("Invitation unavailable")
            if not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(),token_digest):
                raise AccessDenied("Invalid invitation token")
            if not binding or not hmac.compare_digest(binding[0],phone_digest):
                raise AccessDenied("MAX verified phone does not match")
            self._require_director(db,company,director)
            grant_id=str(uuid.uuid4())
            db.execute("UPDATE invitations SET accepted_by=? WHERE id=?",(accountant,invitation_id))
            db.execute("INSERT INTO grants VALUES(?,?,?,?,?,NULL)",
                       (grant_id,invitation_id,company,accountant,scopes))
            self._audit(db,company,accountant,"accept",invitation_id,stamp)
        return grant_id

    def has_access(self, company, accountant, scope):
        if scope not in self.SCOPES:
            return False
        with self._db() as db:
            rows=db.execute("""SELECT g.scopes,i.director FROM grants g
                JOIN invitations i ON g.invitation=i.id
                WHERE g.company=? AND g.accountant=? AND g.revoked IS NULL""",
                (company,accountant)).fetchall()
            return any(scope in scopes.split(",") and db.execute(
                "SELECT 1 FROM directors WHERE company=? AND max_id=? AND revoked IS NULL",
                (company,director)).fetchone() for scopes,director in rows)

    def revoke(self, company, director, accountant, *, now=None):
        stamp=int(time.time() if now is None else now)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_director(db,company,director)
            db.execute("""UPDATE grants SET revoked=? WHERE company=?
                AND accountant=? AND revoked IS NULL""",(stamp,company,accountant))
            self._audit(db,company,director,"revoke",accountant,stamp)
