import pytest
from app.finexpert.delegations import DirectorAccountantRegistry, AccessDenied

def registry(tmp_path):
    r=DirectorAccountantRegistry(tmp_path/"grants.sqlite3", b"synthetic-test-secret-32-bytes-1234567")
    r.add_verified_director("org1","max:director","checked-authority-001")
    return r

def test_confirmed_phone_and_permissions(tmp_path):
    r=registry(tmp_path)
    ident,token=r.invite("org1","max:director","+7 999 123-45-67",
                         {"documents:upload","analysis:run"},now=100)
    assert not r.has_access("org1","max:accountant","documents:upload")
    r.bind_verified_phone("max:accountant","89991234567")
    r.accept(ident,token,"max:accountant",now=120)
    assert r.has_access("org1","max:accountant","documents:upload")
    assert not r.has_access("org1","max:accountant","reports:read")
    assert not r.has_access("org2","max:accountant","documents:upload")
    with pytest.raises(AccessDenied):
        r.accept(ident,token,"max:accountant",now=121)
    r.revoke("org1","max:director","max:accountant",now=130)
    assert not r.has_access("org1","max:accountant","documents:upload")

def test_wrong_phone_and_expiry(tmp_path):
    r=registry(tmp_path)
    ident,token=r.invite("org1","max:director","79991234567",
                         {"analysis:run"},now=100,ttl=50)
    r.bind_verified_phone("max:someone","79990000000")
    with pytest.raises(AccessDenied):
        r.accept(ident,token,"max:someone",now=110)
    r.bind_verified_phone("max:someone","79991234567")
    with pytest.raises(AccessDenied):
        r.accept(ident,token,"max:someone",now=150)

def test_no_self_proclaimed_director(tmp_path):
    r=registry(tmp_path)
    with pytest.raises(AccessDenied):
        r.invite("org1","max:attacker","79991234567",{"documents:upload"})
