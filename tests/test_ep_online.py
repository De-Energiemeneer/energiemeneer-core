from unittest.mock import MagicMock

import pytest
import requests

from energiemeneer_core import ep_online


@pytest.fixture(autouse=True)
def _zet_api_key(monkeypatch):
    monkeypatch.setenv(ep_online._ENV_KEY_EP, "test-ep-key")
    yield


def _resp(status: int = 200, json_data=None, text: str = ""):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.text = text
    return r


def _capture_get(monkeypatch, response):
    calls: list[dict] = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append({"url": url, "headers": headers, "params": params})
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


def test_zoek_op_vbo_succes(monkeypatch):
    resp = _resp(json_data={"label": "A", "registratiedatum": "2024-05-01"})
    calls = _capture_get(monkeypatch, resp)
    r = ep_online.zoek_op_vbo("0518010000404665")
    assert r == {"label": "A", "registratiedatum": "2024-05-01"}
    assert calls[0]["url"].endswith("/PandEnergielabel/AdresseerbaarObject/0518010000404665")
    assert calls[0]["headers"]["Authorization"] == "test-ep-key"


def test_zoek_op_adres_normaliseert_postcode(monkeypatch):
    resp = _resp(json_data={"label": "B"})
    calls = _capture_get(monkeypatch, resp)
    r = ep_online.zoek_op_adres("2548 bv", 8)
    assert r == {"label": "B"}
    assert calls[0]["url"].endswith("/PandEnergielabel/Adres")
    assert calls[0]["params"]["postcode"] == "2548BV"
    assert calls[0]["params"]["huisnummer"] == "8"


def test_zoek_op_adres_stuurt_huisletter_en_toevoeging_mee(monkeypatch):
    """Sub-adres (12A-2): huisletter én toevoeging gaan als queryparameters mee.
    Cruciaal: de functieparameter ``toevoeging`` verlaat het pand als de
    v5-queryparameter ``huisnummertoevoeging`` — een stille naam-verwisseling
    zou pas in productie opvallen (EP-Online negeert onbekende parameters)."""
    resp = _resp(json_data={"label": "C"})
    calls = _capture_get(monkeypatch, resp)
    r = ep_online.zoek_op_adres("2548BV", 12, huisletter="A", toevoeging="2")
    assert r == {"label": "C"}
    assert calls[0]["params"]["huisletter"] == "A"
    assert calls[0]["params"]["huisnummertoevoeging"] == "2"
    assert "toevoeging" not in calls[0]["params"]  # NIET onder de functienaam
    assert calls[0]["params"] == {"postcode": "2548BV", "huisnummer": "12",
                                  "huisletter": "A", "huisnummertoevoeging": "2"}


def test_zoek_op_adres_zonder_subadres_stuurt_exact_de_oude_parameters(monkeypatch):
    """Bestaande aanroepen (pc + huisnummer) blijven byte-gelijk: géén extra keys."""
    calls = _capture_get(monkeypatch, _resp(json_data={"label": "B"}))
    ep_online.zoek_op_adres("2548BV", 8)
    assert calls[0]["params"] == {"postcode": "2548BV", "huisnummer": "8"}


def test_zoek_op_adres_lege_huisletter_of_toevoeging_niet_meegestuurd(monkeypatch):
    """Leeg, None of alleen-spaties → parameter volledig weglaten."""
    calls = _capture_get(monkeypatch, _resp(json_data={"label": "B"}))
    ep_online.zoek_op_adres("2548BV", 8, huisletter="", toevoeging=None)
    ep_online.zoek_op_adres("2548BV", 8, huisletter="  ", toevoeging="  ")
    for c in calls:
        assert c["params"] == {"postcode": "2548BV", "huisnummer": "8"}


def test_zoek_op_adres_stript_spaties_om_subadres(monkeypatch):
    calls = _capture_get(monkeypatch, _resp(json_data={"label": "A"}))
    ep_online.zoek_op_adres("2548BV", 12, huisletter=" A ", toevoeging=" 2 ")
    assert calls[0]["params"]["huisletter"] == "A"
    assert calls[0]["params"]["huisnummertoevoeging"] == "2"


def test_404_op_vbo_geeft_none(monkeypatch):
    _capture_get(monkeypatch, _resp(status=404))
    assert ep_online.zoek_op_vbo("vbo-onbekend") is None


def test_404_op_adres_geeft_none(monkeypatch):
    _capture_get(monkeypatch, _resp(status=404))
    assert ep_online.zoek_op_adres("9999AA", 1) is None


def test_zoek_op_vbo_eist_vbo_id():
    with pytest.raises(ValueError, match="VBO"):
        ep_online.zoek_op_vbo("")
    with pytest.raises(ValueError, match="VBO"):
        ep_online.zoek_op_vbo("   ")


def test_zoek_op_adres_eist_postcode_en_huisnummer():
    with pytest.raises(ValueError, match="Postcode"):
        ep_online.zoek_op_adres("", 8)
    with pytest.raises(ValueError, match="Huisnummer"):
        ep_online.zoek_op_adres("2548BV", "")
    with pytest.raises(ValueError, match="Huisnummer"):
        ep_online.zoek_op_adres("2548BV", None)  # type: ignore[arg-type]


def test_ontbrekende_api_key(monkeypatch):
    monkeypatch.delenv(ep_online._ENV_KEY_EP, raising=False)
    with pytest.raises(RuntimeError, match=ep_online._ENV_KEY_EP):
        ep_online.zoek_op_vbo("vbo-1")


def test_401_geeft_runtime_error(monkeypatch):
    _capture_get(monkeypatch, _resp(status=401))
    with pytest.raises(RuntimeError, match="EP-Online 401"):
        ep_online.zoek_op_vbo("vbo-1")


def test_500_geeft_runtime_error(monkeypatch):
    _capture_get(monkeypatch, _resp(status=500, json_data={"error": "boom"}))
    with pytest.raises(RuntimeError, match="EP-Online 500"):
        ep_online.zoek_op_adres("1234AB", 1)


def test_netwerkfout_geeft_runtime_error(monkeypatch):
    def fake_get(*a, **kw):
        raise requests.ConnectionError("timeout")
    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(RuntimeError, match="EP-Online niet bereikbaar"):
        ep_online.zoek_op_vbo("vbo-1")
