import pytest
from app.agent_catalog import Catalog, CatalogEntry, initial_entries, decode_callback

def test_six_roots_and_nested_routing():
    catalog=Catalog(initial_entries())
    assert len(catalog.children(None))==6
    assert catalog.resolve(("finance","navigation")).route=="accountant"
    assert catalog.resolve(("marketing","competitors")).route=="competitors"
    keyboard=catalog.inline_keyboard(("finance",))
    assert keyboard["payload"]["buttons"][0][0]["payload"]=="catalog:finance/accounting"

def test_new_subagent_without_seventh_bot_or_root():
    rows=initial_entries()
    rows.append(CatalogEntry("seo","SEO-специалист","marketing",route="vk",order=99))
    catalog=Catalog(rows)
    assert len(catalog.children(None))==6
    assert catalog.resolve(("marketing","seo")).title=="SEO-специалист"
    assert decode_callback("catalog:marketing/seo")==("marketing","seo")

def test_disabled_subagent_is_not_resolvable():
    catalog=Catalog(initial_entries()).set_enabled("finance","navigation",False)
    with pytest.raises(ValueError):
        catalog.resolve(("finance","navigation"))
    assert all(row[0]["payload"]!="catalog:finance/navigation"
               for row in catalog.inline_keyboard(("finance",))["payload"]["buttons"])

@pytest.mark.parametrize("payload",["catalog:finance/../../admin","catalog:finance//navigation",
                                    "catalog:__hidden", "agent:developer"])
def test_invalid_or_unavailable_callback(payload):
    catalog=Catalog(initial_entries())
    with pytest.raises(ValueError):
        catalog.resolve(decode_callback(payload))

def test_prevent_unregistered_route_and_parent():
    with pytest.raises(ValueError):
        Catalog(initial_entries()+[CatalogEntry("x","Unsafe","marketing",route="shell")])
    with pytest.raises(ValueError):
        Catalog(initial_entries()+[CatalogEntry("x","Bad parent","missing",route="vk")])
