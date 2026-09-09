"""0.23.1: haal_agenda_op volgt @odata.nextLink (meer dan 100 events)."""
from energiemeneer_core.graph_api import _client, agenda


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._p = payload
        self.text = ""

    def json(self):
        return self._p


def test_haal_agenda_op_volgt_nextlink(monkeypatch):
    aanroepen = []

    def fake_get(pad, *, params=None, headers_extra=None):
        aanroepen.append((pad, params))
        if pad == "/me/calendarView":
            return _Resp({"value": [{"id": "a", "subject": "1", "start": {"dateTime": "2026-09-10T08:00:00.0000000"},
                                     "end": {"dateTime": "2026-09-10T09:30:00.0000000"}}],
                          "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/calendarView?$skip=100"})
        assert pad.startswith("https://") and params is None
        return _Resp({"value": [{"id": "b", "subject": "2", "start": {"dateTime": "2026-09-11T08:00:00.0000000"},
                                 "end": {"dateTime": "2026-09-11T09:30:00.0000000"}}]})

    monkeypatch.setattr(_client, "get", fake_get)
    uit = agenda.haal_agenda_op("2026-09-10T00:00:00Z", "2026-11-10T00:00:00Z")
    assert [e["id"] for e in uit] == ["a", "b"]
    assert len(aanroepen) == 2


def test_client_verzoek_laat_volledige_url_staan(monkeypatch):
    import requests
    from energiemeneer_core import graph_auth
    monkeypatch.setattr(graph_auth, "haal_graph_token", lambda: "AT-test")
    gezien = {}

    def fake_request(methode, url, **kw):
        gezien["url"] = url
        r = _Resp({}); r.status_code = 200
        return r
    monkeypatch.setattr(requests, "request", fake_request)
    _client.verzoek("GET", "https://graph.microsoft.com/v1.0/me/calendarView?$skip=100")
    assert gezien["url"] == "https://graph.microsoft.com/v1.0/me/calendarView?$skip=100"
    _client.verzoek("GET", "/me/events")
    assert gezien["url"] == "https://graph.microsoft.com/v1.0/me/events"
