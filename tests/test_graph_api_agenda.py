from unittest.mock import MagicMock

import pytest
import requests

from energiemeneer_core import graph_auth
from energiemeneer_core.graph_api import _client, agenda


@pytest.fixture(autouse=True)
def _altijd_geldig_token(monkeypatch):
    """haal_graph_token levert in tests altijd meteen een token."""
    monkeypatch.setattr(graph_auth, "haal_graph_token", lambda: "AT-test")
    yield


def _resp(status=200, json_data=None, text=""):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.text = text
    return r


def _vang_request(monkeypatch, *responses):
    """Vervang requests.request; geef opeenvolgende responses terug."""
    calls: list[dict] = []
    seq = list(responses)

    def fake_request(method, url, headers=None, params=None, json=None,
                     data=None, timeout=None):
        calls.append({"method": method, "url": url, "headers": headers,
                      "params": params, "json": json})
        return seq.pop(0) if len(seq) > 1 else seq[0]

    monkeypatch.setattr(requests, "request", fake_request)
    return calls


# ── Agenda ophalen ────────────────────────────────────────────────────────────


def test_haal_agenda_op_geeft_alle_velden_en_geen_filter(monkeypatch):
    resp = _resp(json_data={"value": [
        {"id": "EV-A", "subject": "Opname A", "start": {"dateTime": "2026-06-01T08:00:00.0000000"},
         "end": {"dateTime": "2026-06-01T09:30:00.0000000"}, "isAllDay": False,
         "showAs": "busy", "location": {"displayName": "Graskopstraat 8, 2512EX Den Haag"}},
        {"id": "EV-B", "subject": "Vrij blok", "start": {"dateTime": "2026-06-01T12:00:00Z"},
         "end": {"dateTime": "2026-06-01T13:00:00Z"}, "isAllDay": False,
         "showAs": "free"},
    ]})
    calls = _vang_request(monkeypatch, resp)

    afspraken = agenda.haal_agenda_op("2026-06-01T00:00:00", "2026-06-02T00:00:00")

    # Géén filter: ook de 'free'-afspraak komt terug, met status erbij.
    assert len(afspraken) == 2
    assert afspraken[1]["status"] == "free"
    # Naïeve datetime krijgt een Z; bestaande Z blijft.
    assert afspraken[0]["start"] == "2026-06-01T08:00:00.000Z"
    assert afspraken[1]["start"] == "2026-06-01T12:00:00Z"
    assert afspraken[0]["onderwerp"] == "Opname A"
    # id + locatie komen mee (locatie = adres bij opname-afspraken).
    assert afspraken[0]["id"] == "EV-A"
    assert afspraken[0]["locatie"] == "Graskopstraat 8, 2512EX Den Haag"
    assert afspraken[1]["locatie"] == ""   # geen location → leeg, geen fout
    # UTC wordt afgedwongen via de Prefer-header.
    assert calls[0]["headers"]["Prefer"] == 'outlook.timezone="UTC"'
    assert calls[0]["params"]["startDateTime"] == "2026-06-01T00:00:00"
    assert "location" in calls[0]["params"]["$select"]


def test_haal_agenda_op_eist_periode():
    with pytest.raises(ValueError, match="verplicht"):
        agenda.haal_agenda_op("", "2026-06-02T00:00:00")


def test_haal_agenda_op_fout(monkeypatch):
    _vang_request(monkeypatch, _resp(status=500, text="boom"))
    with pytest.raises(RuntimeError, match="Agenda ophalen mislukt"):
        agenda.haal_agenda_op("2026-06-01T00:00:00", "2026-06-02T00:00:00")


# ── Afspraak aanmaken ──────────────────────────────────────────────────────────


def test_maak_afspraak_stuurt_juiste_payload(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=201, json_data={"id": "EV-1"}))

    r = agenda.maak_afspraak(
        "2026-06-01T08:00:00Z", "2026-06-01T09:30:00Z",
        onderwerp="Energielabel opname",
        body_html="<b>hoi</b>", locatie="Graskopstraat 8, Den Haag",
    )
    assert r == {"id": "EV-1", "onderwerp": "Energielabel opname",
                 "locatie": "Graskopstraat 8, Den Haag"}
    payload = calls[0]["json"]
    assert calls[0]["method"] == "POST"
    assert payload["subject"] == "Energielabel opname"
    # Z is weg, tijdzone apart als UTC.
    assert payload["start"] == {"dateTime": "2026-06-01T08:00:00", "timeZone": "UTC"}
    assert payload["body"] == {"contentType": "html", "content": "<b>hoi</b>"}
    assert payload["location"] == {"displayName": "Graskopstraat 8, Den Haag"}
    assert payload["isReminderOn"] is True
    assert payload["reminderMinutesBeforeStart"] == 60


def test_maak_afspraak_zonder_body_en_zonder_herinnering(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=201, json_data={"id": "EV-2"}))
    agenda.maak_afspraak("2026-06-01T08:00:00Z", "2026-06-01T09:00:00Z",
                         onderwerp="Kort", herinner_minuten=0)
    payload = calls[0]["json"]
    assert "body" not in payload
    assert "location" not in payload
    assert payload["isReminderOn"] is False


def test_maak_afspraak_eist_onderwerp_en_tijden():
    with pytest.raises(ValueError, match="onderwerp"):
        agenda.maak_afspraak("2026-06-01T08:00:00Z", "2026-06-01T09:00:00Z", "")
    with pytest.raises(ValueError, match="start_iso"):
        agenda.maak_afspraak("", "2026-06-01T09:00:00Z", "Titel")


def test_maak_afspraak_fout(monkeypatch):
    _vang_request(monkeypatch, _resp(status=400, text="bad"))
    with pytest.raises(RuntimeError, match="Afspraak aanmaken mislukt"):
        agenda.maak_afspraak("2026-06-01T08:00:00Z", "2026-06-01T09:00:00Z", "Titel")


# ── Afspraak wijzigen ──────────────────────────────────────────────────────────


def test_wijzig_afspraak_alleen_meegegeven_velden(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=200, json_data={}))
    r = agenda.wijzig_afspraak("EV-1", start_iso="2026-06-01T10:00:00Z",
                               eind_iso="2026-06-01T11:00:00Z")
    payload = calls[0]["json"]
    assert calls[0]["method"] == "PATCH"
    assert set(payload.keys()) == {"start", "end"}  # niets anders aangeraakt
    assert payload["start"] == {"dateTime": "2026-06-01T10:00:00", "timeZone": "UTC"}
    assert r == {"id": "EV-1"}


def test_wijzig_afspraak_eist_event_id():
    with pytest.raises(ValueError, match="event_id"):
        agenda.wijzig_afspraak("", onderwerp="x")


def test_wijzig_afspraak_eist_iets_te_wijzigen():
    with pytest.raises(ValueError, match="Niets om te wijzigen"):
        agenda.wijzig_afspraak("EV-1")


# ── Afspraak annuleren ─────────────────────────────────────────────────────────


def test_annuleer_afspraak_404_is_ook_gelukt(monkeypatch):
    _vang_request(monkeypatch, _resp(status=404))
    assert agenda.annuleer_afspraak("EV-weg") is True


def test_annuleer_afspraak_fout(monkeypatch):
    _vang_request(monkeypatch, _resp(status=500, text="boom"))
    with pytest.raises(RuntimeError, match="Afspraak annuleren mislukt"):
        agenda.annuleer_afspraak("EV-1")


def test_annuleer_afspraak_eist_event_id():
    with pytest.raises(ValueError, match="event_id"):
        agenda.annuleer_afspraak("")


# ── Het loket: 401-vangnet ─────────────────────────────────────────────────────


def test_401_leidt_tot_een_herstelpoging(monkeypatch):
    vergeten = {"aantal": 0}
    monkeypatch.setattr(graph_auth, "vergeet_access_token",
                        lambda: vergeten.__setitem__("aantal", vergeten["aantal"] + 1))
    calls = _vang_request(monkeypatch,
                          _resp(status=401, text="expired"),
                          _resp(status=200, json_data={"value": []}))

    afspraken = agenda.haal_agenda_op("2026-06-01T00:00:00", "2026-06-02T00:00:00")
    assert afspraken == []
    assert vergeten["aantal"] == 1          # precies één keer token vergeten
    assert len(calls) == 2                  # en precies één herhaalde aanroep


def test_netwerkfout_geeft_nette_runtime_error(monkeypatch):
    def boom(*a, **kw):
        raise requests.ConnectionError("weg")
    monkeypatch.setattr(requests, "request", boom)
    with pytest.raises(RuntimeError, match="niet bereikbaar"):
        agenda.haal_agenda_op("2026-06-01T00:00:00", "2026-06-02T00:00:00")


def test_mailbox_kiest_de_agenda_van_een_collega(monkeypatch):
    """0.33.0: met mailbox= gaat elke actie naar /users/<adres>, zonder naar /me."""
    calls = _vang_request(
        monkeypatch,
        _resp(status=201, json_data={"id": "EV1"}),
        _resp(status=200, json_data={}),
        _resp(status=204),
        _resp(status=200, json_data={"value": []}),
        _resp(status=201, json_data={"id": "EV2"}),
    )
    mb = "berend@de-energiemeneer.nl"
    agenda.maak_afspraak("2026-11-06T08:00:00Z", "2026-11-06T09:00:00Z", "Opname", mailbox=mb)
    agenda.wijzig_afspraak("EV1", onderwerp="Opname 2", mailbox=mb)
    agenda.annuleer_afspraak("EV1", mailbox=mb)
    agenda.haal_agenda_op("2026-11-06T00:00:00Z", "2026-11-07T00:00:00Z", mailbox=mb)
    agenda.maak_afspraak("2026-11-06T08:00:00Z", "2026-11-06T09:00:00Z", "Opname")
    urls = [c["url"] for c in calls]
    assert urls[0].endswith("/users/berend@de-energiemeneer.nl/events")
    assert urls[1].endswith("/users/berend@de-energiemeneer.nl/events/EV1")
    assert urls[2].endswith("/users/berend@de-energiemeneer.nl/events/EV1")
    assert "/users/berend@de-energiemeneer.nl/calendarView" in urls[3]
    assert urls[4].endswith("/me/events")                      # zonder mailbox: zoals altijd
