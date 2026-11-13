"""Server-side MAX WebApp initData verification."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from fastapi import HTTPException
from .config import settings

def validate_init_data(raw: str, *, now: int | None = None) -> str:
    if not raw or len(raw) > 16384 or not settings.max_bot_token:
        raise HTTPException(status_code=401, detail="MAX authorization required")
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    fields = {}
    for key, val in pairs:
        if key in fields:
            raise HTTPException(status_code=401, detail="Duplicate MAX field")
        fields[key] = val
    given = fields.pop("hash", None)
    if not given or len(given) != 64:
        raise HTTPException(status_code=401, detail="Missing MAX signature")
    signed = "\n".join(f"{key}={val}" for key, val in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", settings.max_bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, signed.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, given):
        raise HTTPException(status_code=401, detail="Invalid MAX signature")
    try:
        auth_date = int(fields["auth_date"])
        user = json.loads(fields["user"])
        user_id = int(user["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Incomplete MAX identity")
    current = int(now if now is not None else time.time())
    if auth_date > current + 60 or current - auth_date > 3600:
        raise HTTPException(status_code=401, detail="Expired MAX launch data")
    if user_id not in settings.allowed_users:
        raise HTTPException(status_code=403, detail="User not allowed")
    return f"max:{user_id}"
