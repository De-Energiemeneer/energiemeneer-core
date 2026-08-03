from unittest.mock import MagicMock

import pytest
import requests

from energiemeneer_core import graph_auth
from energiemeneer_core.graph_api import onedrive


@pytest.fixture(autouse=True)
def _altijd_geldig_token(monkeypatch):
    monkeypatch.setattr(graph_auth, "haal_graph_token", lambda: "AT-test")
    yield


def _resp(status=200, json_data=None, text=""):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.text = text
    return r


def _vang_request(monkeypatch, responder):
    """responder(method, url, json, data) -> Response. Logt alle calls."""
    calls: list[dict] = []

    def fake_request(method, url, headers=None, params=None, json=None,
                     data=None, timeout=None):
        calls.append({"method": method, "url": url, "json": json,
                      "data": data, "headers": headers})
        return responder(method, url, json, data)

    monkeypatch.setattr(requests, "request", fake_request)
    return calls


# ── Map aanmaken ───────────────────────────────────────────────────────────────


def test_maak_map_enkele_nieuwe_map(monkeypatch):
    def responder(method, url, json, data):
        if method == "GET":
            return _resp(status=404)  # bestaat nog niet
        return _resp(status=201, json_data={"id": "F1"})  # POST create

    calls = _vang_request(monkeypatch, responder)
    r = onedrive.maak_map("Energielabels")
    assert r == {"pad": "Energielabels", "mapnaam": "Energielabels"}
    # root-niveau create gaat naar /children
    post = [c for c in calls if c["method"] == "POST"][0]
    assert post["url"].endswith("/me/drive/root/children")
    assert post["json"]["name"] == "Energielabels"


def test_maak_map_slaat_bestaande_tussenmappen_over(monkeypatch):
    # "A/B/C": A en B bestaan al, C is nieuw.
    bestaande = {"A", "A/B"}

    def responder(method, url, json, data):
        if method == "GET":
            pad = url.split("/me/drive/root:/", 1)[1]
            return _resp(status=200) if pad in bestaande else _resp(status=404)
        return _resp(status=201, json_data={"id": "x"})

    calls = _vang_request(monkeypatch, responder)
    r = onedrive.maak_map("A/B/C")
    assert r["pad"] == "A/B/C" and r["mapnaam"] == "C"
    # Alleen C wordt aangemaakt (A en B bestonden al).
    posts = [c for c in calls if c["method"] == "POST"]
    assert len(posts) == 1
    assert posts[0]["json"]["name"] == "C"
    assert posts[0]["url"].endswith("/me/drive/root:/A/B:/children")


def test_maak_map_unieke_naam_bij_botsing(monkeypatch):
    # "Klanten/Straat 8" bestaat al, "Klanten/Straat 8_1" niet.
    bestaande = {"Klanten", "Klanten/Straat 8"}

    def responder(method, url, json, data):
        if method == "GET":
            pad = url.split("/me/drive/root:/", 1)[1]
            return _resp(status=200) if pad in bestaande else _resp(status=404)
        return _resp(status=201, json_data={"id": "x"})

    calls = _vang_request(monkeypatch, responder)
    r = onedrive.maak_map("Klanten/Straat 8")
    assert r["mapnaam"] == "Straat 8_1"
    assert r["pad"] == "Klanten/Straat 8_1"
    post = [c for c in calls if c["method"] == "POST"][0]
    assert post["json"]["name"] == "Straat 8_1"


def test_maak_map_eist_pad():
    with pytest.raises(ValueError, match="pad is verplicht"):
        onedrive.maak_map("   ")


def test_maak_map_fout_bij_controle(monkeypatch):
    _vang_request(monkeypatch, lambda *a: _resp(status=500, text="boom"))
    with pytest.raises(RuntimeError, match="controleren mislukt"):
        onedrive.maak_map("X")


# ── Upload: klein ──────────────────────────────────────────────────────────────


def test_upload_klein_bestand(monkeypatch, tmp_path):
    bestand = tmp_path / "doc.pdf"
    bestand.write_bytes(b"kleine inhoud")

    calls = _vang_request(monkeypatch, lambda *a: _resp(status=201))
    r = onedrive.upload_bestand(str(bestand), "Map/doc.pdf")
    assert r == {"pad": "Map/doc.pdf", "grootte": len(b"kleine inhoud")}
    assert calls[0]["method"] == "PUT"
    assert calls[0]["url"].endswith("/me/drive/root:/Map/doc.pdf:/content")
    assert calls[0]["data"] == b"kleine inhoud"
    assert calls[0]["headers"]["Content-Type"] == "application/octet-stream"


def test_upload_eist_doelpad(tmp_path):
    bestand = tmp_path / "x.txt"
    bestand.write_bytes(b"x")
    with pytest.raises(ValueError, match="onedrive_pad"):
        onedrive.upload_bestand(str(bestand), "")


def test_upload_bestand_niet_gevonden():
    with pytest.raises(RuntimeError, match="niet gevonden"):
        onedrive.upload_bestand("/bestaat/niet.txt", "Map/x.txt")


def test_upload_klein_fout(monkeypatch, tmp_path):
    bestand = tmp_path / "doc.pdf"
    bestand.write_bytes(b"data")
    _vang_request(monkeypatch, lambda *a: _resp(status=403, text="nee"))
    with pytest.raises(RuntimeError, match="Upload mislukt"):
        onedrive.upload_bestand(str(bestand), "Map/doc.pdf")


# ── Upload: groot (upload-sessie in stukjes) ───────────────────────────────────


def test_upload_groot_bestand_in_stukjes(monkeypatch, tmp_path):
    # Verlaag grenzen zodat een klein testbestand de 'grote' weg neemt.
    monkeypatch.setattr(onedrive, "_SIMPEL_MAX", 4)
    monkeypatch.setattr(onedrive, "_CHUNK", 4)

    bestand = tmp_path / "groot.bin"
    bestand.write_bytes(b"0123456789")  # 10 bytes -> 3 brokken van 4/4/2

    # createUploadSession loopt via requests.request (POST).
    def responder(method, url, json, data):
        return _resp(status=200, json_data={"uploadUrl": "https://upload.example/sessie"})

    req_calls = _vang_request(monkeypatch, responder)

    # De brokken gaan via requests.put naar de uploadUrl.
    put_calls: list[dict] = []

    def fake_put(url, data=None, headers=None, timeout=None):
        bereik = headers["Content-Range"]
        put_calls.append({"url": url, "len": len(data), "range": bereik})
        # Laatste brok ("bytes 8-9/10"): 201 klaar; tussenbrokken: 202.
        eind, totaal = bereik.split(" ")[1].split("/")
        laatste = int(eind.split("-")[1]) == int(totaal) - 1
        return _resp(status=201 if laatste else 202)

    monkeypatch.setattr(requests, "put", fake_put)

    r = onedrive.upload_bestand(str(bestand), "Map/groot.bin")
    assert r["grootte"] == 10
    # createUploadSession is aangevraagd.
    assert any("createUploadSession" in c["url"] for c in req_calls)
    # 3 brokken: 0-3, 4-7, 8-9.
    assert [c["range"] for c in put_calls] == [
        "bytes 0-3/10", "bytes 4-7/10", "bytes 8-9/10",
    ]
    assert [c["len"] for c in put_calls] == [4, 4, 2]


def test_upload_groot_sessie_fout(monkeypatch, tmp_path):
    monkeypatch.setattr(onedrive, "_SIMPEL_MAX", 1)
    bestand = tmp_path / "groot.bin"
    bestand.write_bytes(b"abcd")
    _vang_request(monkeypatch, lambda *a: _resp(status=500, text="nee"))
    with pytest.raises(RuntimeError, match="Upload-sessie aanvragen mislukt"):
        onedrive.upload_bestand(str(bestand), "Map/groot.bin")


# ── web_url ─────────────────────────────────────────────────────────────────────


def test_web_url_gevonden(monkeypatch):
    def responder(method, url, json, data):
        return _resp(status=200, json_data={"webUrl": "https://onedrive/x/Straat 8"})
    _vang_request(monkeypatch, responder)
    assert onedrive.web_url("1. Werkmap/Energielabels/Straat 8") == "https://onedrive/x/Straat 8"


def test_web_url_niet_gevonden_geeft_leeg(monkeypatch):
    _vang_request(monkeypatch, lambda *a: _resp(status=404))
    assert onedrive.web_url("bestaat/niet") == ""


def test_web_url_leeg_pad(monkeypatch):
    assert onedrive.web_url("") == ""


# ── download_bestand ─────────────────────────────────────────────────────────


def _resp_content(status=200, content=b""):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.content = content
    return r


def test_download_bestand_schrijft_lokaal(monkeypatch, tmp_path):
    calls = _vang_request(monkeypatch, lambda *a: _resp_content(200, b"%PDF-fake-bytes"))
    doel = tmp_path / "label.pdf"
    uit = onedrive.download_bestand("1. Werkmap/Energielabels/Straat 8/label.pdf", str(doel))
    assert uit == str(doel)
    assert doel.read_bytes() == b"%PDF-fake-bytes"
    assert calls[-1]["url"].endswith(":/content")


def test_download_bestand_eist_bronpad():
    with pytest.raises(ValueError):
        onedrive.download_bestand("", "/tmp/x.pdf")


def test_download_bestand_fout(monkeypatch, tmp_path):
    _vang_request(monkeypatch, lambda *a: _resp_content(404, b""))
    with pytest.raises(RuntimeError):
        onedrive.download_bestand("bestaat/niet.pdf", str(tmp_path / "x.pdf"))


# ── Mapinhoud opsommen ─────────────────────────────────────────────────────────


def test_lijst_bestanden_geeft_naam_grootte_en_mapvlag(monkeypatch):
    waarde = {"value": [
        {"name": "foto1.jpg", "size": 1234, "file": {}},
        {"name": "Submap", "size": 0, "folder": {"childCount": 2}},
    ]}

    def responder(method, url, json, data):
        return _resp(status=200, json_data=waarde)

    calls = _vang_request(monkeypatch, responder)
    res = onedrive.lijst_bestanden("Dossiers/Straat 8")
    assert res == [
        {"naam": "foto1.jpg", "grootte": 1234, "is_map": False},
        {"naam": "Submap", "grootte": 0, "is_map": True},
    ]
    assert calls[0]["url"].endswith("/me/drive/root:/Dossiers/Straat 8:/children")


def test_lijst_bestanden_volgt_paginering(monkeypatch):
    pagina1 = {
        "value": [{"name": "a.pdf", "size": 1, "file": {}}],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/drive/items/x/children?$skiptoken=abc",
    }
    pagina2 = {"value": [{"name": "b.pdf", "size": 2, "file": {}}]}

    def responder(method, url, json, data):
        return _resp(status=200, json_data=pagina2 if "skiptoken" in url else pagina1)

    _vang_request(monkeypatch, responder)
    res = onedrive.lijst_bestanden("Map")
    assert [i["naam"] for i in res] == ["a.pdf", "b.pdf"]


def test_lijst_bestanden_map_niet_gevonden(monkeypatch):
    _vang_request(monkeypatch, lambda m, u, j, d: _resp(status=404))
    with pytest.raises(RuntimeError, match="niet gevonden"):
        onedrive.lijst_bestanden("Bestaat/Niet")


def test_lijst_bestanden_eist_pad():
    with pytest.raises(ValueError):
        onedrive.lijst_bestanden("")


# ── Item verplaatsen ───────────────────────────────────────────────────────────


def test_verplaats_item_naar_bestaande_doelmap(monkeypatch):
    def responder(method, url, json, data):
        if method == "GET":
            return _resp(status=200)  # doelmap bestaat al
        if method == "PATCH":
            return _resp(status=200, json_data={"name": "Straat 8, Delft"})
        return _resp(status=500)

    calls = _vang_request(monkeypatch, responder)
    r = onedrive.verplaats_item("Voorbereiding/Straat 8, Delft", "1. Afgerond")
    assert r == {"pad": "1. Afgerond/Straat 8, Delft", "naam": "Straat 8, Delft"}
    patch = [c for c in calls if c["method"] == "PATCH"][0]
    assert patch["url"].endswith("/me/drive/root:/Voorbereiding/Straat 8, Delft")
    assert patch["json"]["parentReference"]["path"] == "/drive/root:/1. Afgerond"
    assert patch["json"]["@microsoft.graph.conflictBehavior"] == "rename"


def test_verplaats_item_maakt_ontbrekende_doelmap_aan(monkeypatch):
    def responder(method, url, json, data):
        if method == "GET":
            return _resp(status=404)  # doelmap bestaat nog niet
        if method == "POST":
            return _resp(status=201, json_data={"id": "F1"})
        if method == "PATCH":
            return _resp(status=200, json_data={"name": "Straat 8"})
        return _resp(status=500)

    calls = _vang_request(monkeypatch, responder)
    r = onedrive.verplaats_item("Voorbereiding/Straat 8", "Werkmap/1. Afgerond")
    assert r["pad"] == "Werkmap/1. Afgerond/Straat 8"
    # Beide segmenten van de doelmap worden aangemaakt.
    posts = [c for c in calls if c["method"] == "POST"]
    assert [p["json"]["name"] for p in posts] == ["Werkmap", "1. Afgerond"]


def test_verplaats_item_hernoemd_bij_naamsbotsing(monkeypatch):
    def responder(method, url, json, data):
        if method == "GET":
            return _resp(status=200)
        if method == "PATCH":
            return _resp(status=200, json_data={"name": "Straat 8 1"})  # OneDrive hernoemt
        return _resp(status=500)

    _vang_request(monkeypatch, responder)
    r = onedrive.verplaats_item("Voorbereiding/Straat 8", "Afgerond")
    assert r == {"pad": "Afgerond/Straat 8 1", "naam": "Straat 8 1"}


def test_verplaats_item_bron_niet_gevonden(monkeypatch):
    def responder(method, url, json, data):
        if method == "GET":
            return _resp(status=200)
        if method == "PATCH":
            return _resp(status=404)
        return _resp(status=500)

    _vang_request(monkeypatch, responder)
    with pytest.raises(RuntimeError, match="niet gevonden"):
        onedrive.verplaats_item("Weg/Item", "Afgerond")


def test_verplaats_item_eist_paden():
    with pytest.raises(ValueError):
        onedrive.verplaats_item("", "Afgerond")
    with pytest.raises(ValueError):
        onedrive.verplaats_item("Iets", "")
