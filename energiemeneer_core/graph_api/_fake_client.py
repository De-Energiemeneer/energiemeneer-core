"""Fake Microsoft Graph-client voor dev/test zonder echte Microsoft 365-tenant.

Wordt ingeschakeld door :mod:`energiemeneer_core.graph_api._client` zodra
:func:`energiemeneer_core.environment.use_fake_clients` waar is. Geeft objecten
terug met dezelfde vorm als ``requests.Response`` (``status_code``, ``json()``,
``text``, ``headers``), zodat de aanroepende modules niets merken.

- **Writes** (sendMail, agenda, OneDrive, OneNote, ToDo) doen niets echt: ze
  loggen een ``[FAKE]``-regel en geven een succes-vormige respons.
- **Reads** geven minimale fixtures die qua structuur matchen met wat de echte
  Graph teruggeeft (lege collecties waar de caller dat verdraagt, één minimaal
  item waar hij er minstens één nodig heeft).

Bewust een *leaf*-module: importeert alleen de standaardbibliotheek, zodat er
geen circulaire imports ontstaan. De auth-stub (token, device-login) zit niet
hier maar in :mod:`energiemeneer_core.graph_auth`.

OneNote heeft een kleine **stateful** in-memory store (notitieboeken/secties/
pagina's), zodat ``kopieer_sjabloonpagina`` end-to-end draait: zoeken op naam,
kopiëren (async-operatie) en hernoemen werken allemaal. De store start met een
standaard-seed (notitieboek "De Energiemeneer", sectie "Opnames", sjabloon
"Adres"); tests kunnen 'm vervangen via :func:`seed_onenote` of resetten via
:func:`reset_onenote`.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any

_log = logging.getLogger(__name__)

# Eén minimaal bericht voor de mailbox-scan — qua structuur gelijk aan Graph.
_FAKE_BERICHT = {
    "id": "fake-msg-1",
    "subject": "[FAKE] Voorbeeldbericht",
    "from": {"emailAddress": {"address": "noreply@fake.local"}},
    "receivedDateTime": "2026-01-01T00:00:00Z",
    "hasAttachments": False,
}


class _FakeResponse:
    """Minimale ``requests.Response``-vorm: ``status_code``/``json()``/``text``/``headers``."""

    def __init__(
        self,
        status_code: int,
        json_data: Any = None,
        *,
        text: str = "",
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self._json = {} if json_data is None else json_data
        self.text = text
        self.headers = headers or {}

    def json(self) -> Any:
        return self._json


def verzoek(
    methode: str,
    pad: str,
    *,
    params: Any = None,
    json: Any = None,
    data: Any = None,
    headers_extra: dict[str, str] | None = None,
    timeout: int = 15,
) -> _FakeResponse:
    """Beantwoord een Graph-aanroep met een fake respons (geen netwerk)."""
    return _dispatch((methode or "").upper(), pad, json, data)


def _dispatch(m: str, pad: str, json: Any = None, data: Any = None) -> _FakeResponse:
    # ── Agenda / mail / events (writes) ──────────────────────────────────────
    if m == "POST" and pad == "/me/sendMail":
        _log.info("[FAKE] POST /me/sendMail — niet echt verzonden")
        return _FakeResponse(202)
    if m == "POST" and pad == "/me/events":
        _log.info("[FAKE] POST /me/events — afspraak niet echt aangemaakt")
        return _FakeResponse(201, {"id": "fake-event-1"})
    if m == "PATCH" and pad.startswith("/me/events/"):
        _log.info("[FAKE] PATCH %s — afspraak niet echt gewijzigd", pad)
        return _FakeResponse(200, {"id": pad.rsplit("/", 1)[-1]})
    if m == "DELETE" and pad.startswith("/me/events/"):
        _log.info("[FAKE] DELETE %s — afspraak niet echt geannuleerd", pad)
        return _FakeResponse(204)

    # ── ToDo ─────────────────────────────────────────────────────────────────
    if m == "POST" and pad == "/me/todo/lists":
        _log.info("[FAKE] POST /me/todo/lists — lijst niet echt aangemaakt")
        return _FakeResponse(201, {"id": "fake-list-1"})
    if m == "POST" and pad.endswith("/tasks"):
        _log.info("[FAKE] POST %s — taak niet echt aangemaakt", pad)
        return _FakeResponse(201, {"id": "fake-task-1"})
    if m == "GET" and (pad == "/me/todo/lists" or pad.endswith("/tasks")):
        return _FakeResponse(200, {"value": []})

    # ── OneDrive ─────────────────────────────────────────────────────────────
    if m == "PUT" and pad.endswith(":/content"):
        _log.info("[FAKE] PUT %s — bestand niet echt geüpload", pad)
        return _FakeResponse(
            201, {"id": "fake-file-1", "webUrl": "https://fake.local/bestand"}
        )
    if m == "POST" and pad.endswith(":/createUploadSession"):
        return _FakeResponse(200, {"uploadUrl": "https://fake.local/upload-session"})
    if m == "POST" and pad.endswith("/children"):
        _log.info("[FAKE] POST %s — map niet echt aangemaakt", pad)
        return _FakeResponse(201, {"id": "fake-folder-1"})
    if m == "GET" and pad.startswith("/me/drive/root"):
        # 'bestaat nog niet' -> maak_map gaat netjes door met aanmaken;
        # web_url geeft "" terug bij non-200 (geen fout).
        return _FakeResponse(404, text="[FAKE] pad bestaat niet")

    # ── OneNote (stateful: kopieerflow draait end-to-end) ────────────────────
    if pad.startswith("/me/onenote") or pad.endswith("/copyToSection"):
        antwoord = _onenote_dispatch(m, pad, json, data)
        if antwoord is not None:
            return antwoord

    # ── Mail (reads) ─────────────────────────────────────────────────────────
    if m == "GET" and pad.endswith("/attachments"):
        return _FakeResponse(200, {"value": []})
    if m == "GET" and pad == "/me/messages":
        return _FakeResponse(200, {"value": [_FAKE_BERICHT]})
    if m == "GET" and pad.startswith("/me/mailFolders/") and pad.endswith("/messages"):
        # Map-specifiek zoeken (bijv. Verzonden items) → zelfde fake bericht.
        return _FakeResponse(200, {"value": [_FAKE_BERICHT]})
    if m == "GET" and (pad == "/me/mailFolders" or pad.endswith("/childFolders")):
        # Mailmappen opsommen (zoek_mailmap_id) → geen gebruikersmappen in fake.
        return _FakeResponse(200, {"value": []})
    if m == "GET" and pad.startswith("/me/messages/"):
        # Eén bericht ophalen (haal_bericht) → het fake bericht als object.
        return _FakeResponse(200, dict(_FAKE_BERICHT, body={"contentType": "HTML",
                                                            "content": "<p>[FAKE] body</p>"}))

    # ── Agenda (read) ────────────────────────────────────────────────────────
    if m == "GET" and pad.startswith("/me/calendarView"):
        return _FakeResponse(200, {"value": []})

    # Onbekend pad: log en geef een lege, geldige respons (nooit crashen).
    _log.warning("[FAKE] onbekende Graph-aanroep %s %s — lege respons", m, pad)
    return _FakeResponse(200, {"value": []})


# ── Stateful OneNote ─────────────────────────────────────────────────────────


_onenote: dict = {}


def _default_onenote() -> dict:
    """De standaard-seed: de echte De Energiemeneer-namen (zie onenote-docstring)."""
    return {
        "notebooks": [
            {
                "id": "nb-1",
                "displayName": "De Energiemeneer",
                "sections": [
                    {
                        "id": "sec-1",
                        "displayName": "Opnames",
                        "pages": [{"id": "pg-adres", "title": "Adres"}],
                    }
                ],
            }
        ],
        "operations": {},
        "teller": 0,
    }


def reset_onenote() -> None:
    """Zet de fake-OneNote terug op de standaard-seed."""
    global _onenote
    _onenote = _default_onenote()


def seed_onenote(notebooks: list[dict]) -> None:
    """Vervang de fake-OneNote door een eigen structuur (voor tests).

    ``notebooks`` is ``[{displayName, sections: [{displayName, pages:
    [{title}]}]}]``; id's worden automatisch toegekend.
    """
    global _onenote
    _onenote = {"notebooks": [], "operations": {}, "teller": 0}
    for nb in notebooks:
        secties = []
        for sec in nb.get("sections", []):
            paginas = [
                {"id": _nieuw_id("pg"), "title": p["title"]}
                for p in sec.get("pages", [])
            ]
            secties.append(
                {"id": _nieuw_id("sec"), "displayName": sec["displayName"], "pages": paginas}
            )
        _onenote["notebooks"].append(
            {"id": _nieuw_id("nb"), "displayName": nb["displayName"], "sections": secties}
        )


def _nieuw_id(prefix: str) -> str:
    _onenote["teller"] += 1
    return f"{prefix}-{_onenote['teller']}"


def _vind_notebook(nbid: str) -> dict | None:
    return next((nb for nb in _onenote["notebooks"] if nb["id"] == nbid), None)


def _vind_sectie(secid: str) -> dict | None:
    for nb in _onenote["notebooks"]:
        for sec in nb["sections"]:
            if sec["id"] == secid:
                return sec
    return None


def _vind_pagina(pageid: str) -> dict | None:
    for nb in _onenote["notebooks"]:
        for sec in nb["sections"]:
            for p in sec["pages"]:
                if p["id"] == pageid:
                    return p
    return None


def _titel_uit_patch(commando: Any) -> str | None:
    """Lees de nieuwe titel uit een content-PATCH ([{target:title, content:...}])."""
    if isinstance(commando, list):
        for c in commando:
            if isinstance(c, dict) and c.get("target") == "title":
                return c.get("content")
    return None


def _titel_uit_xhtml(data: Any) -> str:
    """Haal de <title> uit de XHTML-body van een lege-pagina-POST."""
    if not data:
        return ""
    tekst = data.decode("utf-8", "ignore") if isinstance(data, (bytes, bytearray)) else str(data)
    m = re.search(r"<title>(.*?)</title>", tekst, re.IGNORECASE | re.DOTALL)
    return html.unescape(m.group(1)) if m else ""


def _onenote_dispatch(m: str, pad: str, json: Any, data: Any) -> _FakeResponse | None:
    """Beantwoord OneNote-aanroepen tegen de in-memory store; None = geen match."""
    delen = [d for d in pad.split("/") if d]  # ['me', 'onenote', ...]
    if len(delen) < 3:
        return None

    if m == "GET" and pad == "/me/onenote/notebooks":
        return _FakeResponse(200, {"value": [
            {"id": nb["id"], "displayName": nb["displayName"]}
            for nb in _onenote["notebooks"]
        ]})

    if m == "GET" and delen[2] == "notebooks" and delen[-1] == "sections":
        nb = _vind_notebook(delen[3])
        secties = nb["sections"] if nb else []
        return _FakeResponse(200, {"value": [
            {"id": s["id"], "displayName": s["displayName"]} for s in secties
        ]})

    if m == "GET" and delen[2] == "sections" and delen[-1] == "pages":
        sec = _vind_sectie(delen[3])
        paginas = sec["pages"] if sec else []
        return _FakeResponse(200, {"value": [
            {"id": p["id"], "title": p["title"]} for p in paginas
        ]})

    if m == "POST" and delen[2] == "pages" and delen[-1] == "copyToSection":
        bron = _vind_pagina(delen[3])
        doel = _vind_sectie((json or {}).get("id", ""))
        nieuwe = {"id": _nieuw_id("pg"), "title": bron["title"] if bron else ""}
        if doel is not None:
            doel["pages"].append(nieuwe)
        opid = _nieuw_id("op")
        _onenote["operations"][opid] = nieuwe["id"]
        _log.info("[FAKE] OneNote-kopie gestart (op %s -> pagina %s)", opid, nieuwe["id"])
        return _FakeResponse(
            202, {"id": opid},
            headers={"Operation-Location": f"/me/onenote/operations/{opid}"},
        )

    if m == "GET" and delen[2] == "operations":
        page_id = _onenote["operations"].get(delen[3], "fake-page")
        return _FakeResponse(200, {"status": "completed", "resourceId": page_id})

    if m == "PATCH" and delen[2] == "pages" and delen[-1] == "content":
        pagina = _vind_pagina(delen[3])
        nieuwe_titel = _titel_uit_patch(json)
        if pagina is not None and nieuwe_titel is not None:
            pagina["title"] = nieuwe_titel
        _log.info("[FAKE] OneNote-pagina %s hernoemd naar %r", delen[3], nieuwe_titel)
        return _FakeResponse(204)

    if m == "POST" and delen[2] == "sections" and delen[-1] == "pages":
        sec = _vind_sectie(delen[3])
        nieuwe = {"id": _nieuw_id("pg"), "title": _titel_uit_xhtml(data)}
        if sec is not None:
            sec["pages"].append(nieuwe)
        _log.info("[FAKE] OneNote lege pagina aangemaakt: %s", nieuwe["id"])
        return _FakeResponse(201, {"id": nieuwe["id"]})

    return None


reset_onenote()  # initialiseer de store bij import
