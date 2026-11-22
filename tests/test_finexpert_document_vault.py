"""Synthetic data only; no client documents."""
import pytest
from cryptography.fernet import Fernet
from app.finexpert.document_vault import DocumentVault, VaultError


def test_original_immutable_and_versions_linked(tmp_path):
    vault = DocumentVault(tmp_path, Fernet.generate_key())
    source = b"DEMO invoice: Person Name; 100 RUB"
    original = vault.ingest_original("tenant_1", "org_1", source)
    sanitized = vault.store_sanitized("tenant_1", "org_1", original, b"DEMO invoice: Party_001; 100 RUB")
    result = vault.store_result("tenant_1", "org_1", sanitized, {"status": "demo"})
    assert vault.read("tenant_1", "org_1", original) == source
    assert vault.read("tenant_1", "org_1", sanitized) != source
    records = {r["id"]: r for r in vault.list_artifacts("tenant_1", "org_1")}
    assert records[original]["parent_id"] is None
    assert records[sanitized]["parent_id"] == original
    assert records[result]["parent_id"] == sanitized
    second = vault.store_sanitized("tenant_1", "org_1", original, b"DEMO invoice: Party_002; 100 RUB")
    assert second != sanitized
    assert vault.read("tenant_1", "org_1", original) == source


def test_cross_tenant_and_cross_org_isolation(tmp_path):
    vault = DocumentVault(tmp_path, Fernet.generate_key())
    original = vault.ingest_original("tenant_1", "org_1", b"DEMO")
    for tenant, org in [("tenant_2", "org_1"), ("tenant_1", "org_2")]:
        with pytest.raises(VaultError):
            vault.read(tenant, org, original)
        with pytest.raises(VaultError):
            vault.store_sanitized(tenant, org, original, b"Redacted")


def test_wrong_parent_for_results(tmp_path):
    vault = DocumentVault(tmp_path, Fernet.generate_key())
    original = vault.ingest_original("tenant_1", "org_1", b"DEMO")
    with pytest.raises(VaultError):
        vault.store_result("tenant_1", "org_1", original, {"x": 1})


def test_no_plaintext_on_disk_and_no_filename_collisions(tmp_path):
    key = Fernet.generate_key()
    vault = DocumentVault(tmp_path, key)
    original = vault.ingest_original("tenant_1", "org_1", b"DEMO extremely private")
    vault.ingest_original("tenant_1", "org_1", b"DEMO extremely private")
    assert len(vault.list_artifacts("tenant_1", "org_1")) == 2
    assert b"extremely private" not in b"".join(p.read_bytes() for p in tmp_path.glob("*.encrypted"))
    assert vault.read("tenant_1", "org_1", original) == b"DEMO extremely private"
