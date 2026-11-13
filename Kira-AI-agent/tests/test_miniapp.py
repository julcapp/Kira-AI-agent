import hashlib, hmac, json, time
from urllib.parse import urlencode
import pytest
from fastapi import HTTPException
from app.miniapp_auth import validate_init_data
from app.config import settings

def make_data(token="test-token", user_id=42):
    fields={"auth_date":str(int(time.time())),"user":json.dumps({"id":user_id},separators=(",",":"))}
    signed="\n".join(f"{k}={v}" for k,v in sorted(fields.items()))
    secret=hmac.new(b"WebAppData",token.encode(),hashlib.sha256).digest()
    fields["hash"]=hmac.new(secret,signed.encode(),hashlib.sha256).hexdigest()
    return urlencode(fields)

def test_max_initdata_valid(monkeypatch):
    monkeypatch.setattr(settings,"max_bot_token","test-token")
    monkeypatch.setattr(settings,"max_allowed_user_ids","42")
    assert validate_init_data(make_data())=="max:42"

def test_max_initdata_forgery_rejected(monkeypatch):
    monkeypatch.setattr(settings,"max_bot_token","test-token")
    monkeypatch.setattr(settings,"max_allowed_user_ids","42")
    with pytest.raises(HTTPException) as err:
        validate_init_data(make_data().replace("42","43",1))
    assert err.value.status_code == 401

def test_max_initdata_non_owner_rejected(monkeypatch):
    monkeypatch.setattr(settings,"max_bot_token","test-token")
    monkeypatch.setattr(settings,"max_allowed_user_ids","42")
    with pytest.raises(HTTPException) as err:
        validate_init_data(make_data(user_id=99))
    assert err.value.status_code == 403

def test_max_initdata_expired(monkeypatch):
    monkeypatch.setattr(settings,"max_bot_token","test-token")
    monkeypatch.setattr(settings,"max_allowed_user_ids","42")
    with pytest.raises(HTTPException) as err:
        validate_init_data(make_data(),now=int(time.time())+4000)
    assert err.value.status_code == 401
