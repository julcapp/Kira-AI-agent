import pytest
from app.max_menu import CATALOG, keyboard, resolve_callback

def test_main_menu_has_six_sections():
    keys = [x.key for x in CATALOG]
    assert keys == ["lawyer","finexpert","manager","marketing","developer","teacher"]
    rows=keyboard()["payload"]["buttons"]
    assert rows[0][0]["payload"]=="menu:lawyer"
    assert rows[-1][0]["payload"]=="menu:"

def test_accountant_menu_and_navigation():
    assert resolve_callback("menu:finexpert")==("menu",("finexpert",),None)
    kind,path,agent=resolve_callback("menu:finexpert/accounting")
    assert (kind,agent)==("agent","accountant")
    assert resolve_callback("menu:finexpert/financial_navigation")[2]=="accountant"
    rows=keyboard(("finexpert",))["payload"]["buttons"]
    assert rows[-2][0]["payload"]=="menu:"
    assert rows[-1][0]["payload"]=="menu:"

@pytest.mark.parametrize("raw", ["menu:unknown","menu:developer/shell","menu:../root",
                                   "menu:lawyer///debt","agent:lawyer","menu:finexpert/other"])
def test_invalid_callback_rejected(raw):
    with pytest.raises(ValueError):
        resolve_callback(raw)
