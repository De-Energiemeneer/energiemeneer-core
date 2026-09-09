"""Outlook-agenda via Microsoft Graph — de generieke afspraak-machine.

Bron: ``admin-portal/admin-portal/ms_graph.py`` (de schoonste agenda-CRUD).
Bewust generiek gehouden: deze module weet *hoe* je een afspraak ophaalt,
maakt, wijzigt of annuleert — niet *wat* erin staat. De vaste EnergieMeneer-
opmaak (titel/body van een opname) komt in Module 7 (``agenda_format``).

Tijden lopen consequent in UTC: ``haal_agenda_op`` geeft UTC-ISO terug
(eindigend op ``Z``) en bij aanmaken/wijzigen geef je UTC-ISO mee. Microsoft
toont dat vanzelf in de juiste lokale tijd in Kevins agenda.

Zie BOUWPLAN.md, Module 6 (onderdeel 1).
"""

from __future__ import annotations

import logging
from typing import Any

from energiemeneer_core.graph_api import _client

_log = logging.getLogger(__name__)


def haal_agenda_op(start_iso: str, eind_iso: str) -> list[dict[str, Any]]:
    """Geef alle afspraken in een periode terug.

    Args:
        start_iso: begin van de periode als ISO-tijd (UTC).
        eind_iso: einde van de periode als ISO-tijd (UTC).

    Returns:
        Lijst van dicts met ``id`` (de Outlook event-id), ``onderwerp``,
        ``start``, ``eind`` (UTC-ISO, eindigend op ``Z``), ``hele_dag``,
        ``status`` (de Outlook ``showAs``-waarde: ``busy``/``free``/
        ``tentative``/…) en ``locatie`` (de ``location.displayName`` — bij
        opname-afspraken het adres). Er wordt **niet** gefilterd — de
        aanroeper bepaalt zelf wat relevant is.

    Raises:
        ValueError: start- of eindtijd ontbreekt.
        RuntimeError: Graph geeft een fout.
    """
    if not start_iso or not eind_iso:
        raise ValueError("start_iso en eind_iso zijn verplicht")

    pad = "/me/calendarView"
    params = {
        "startDateTime": start_iso,
        "endDateTime": eind_iso,
        "$select": "id,subject,start,end,isAllDay,showAs,location",
        "$top": 100,
        "$orderby": "start/dateTime",
    }
    afspraken = []
    # Paginering (0.23.1): Graph geeft maximaal $top items per pagina en een
    # @odata.nextLink voor de rest. Vóór 0.23.1 stopte de lijst bij 100 events,
    # waardoor een volle agenda valse vrije slots opleverde. Harde bovengrens
    # tegen een oneindige lus.
    for _ in range(100):
        resp = _client.get(
            pad,
            params=params,
            # Prefer-header dwingt Graph om in UTC te antwoorden.
            headers_extra={"Prefer": 'outlook.timezone="UTC"'},
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Agenda ophalen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        data = resp.json()
        for ev in data.get("value", []):
            afspraken.append(
                {
                    "id": ev.get("id", ""),
                    "onderwerp": ev.get("subject", ""),
                    "start": _naar_utc_iso(ev.get("start", {}).get("dateTime", "")),
                    "eind": _naar_utc_iso(ev.get("end", {}).get("dateTime", "")),
                    "hele_dag": ev.get("isAllDay", False),
                    "status": ev.get("showAs", ""),
                    "locatie": (ev.get("location", {}) or {}).get("displayName", ""),
                }
            )
        volgende = data.get("@odata.nextLink")
        if not volgende:
            break
        pad, params = volgende, None
    return afspraken


def maak_afspraak(
    start_iso: str,
    eind_iso: str,
    onderwerp: str,
    body_html: str = "",
    locatie: str = "",
    herinner_minuten: int = 60,
) -> dict[str, Any]:
    """Maak een Outlook-afspraak aan.

    Args:
        start_iso, eind_iso: begin/eind als ISO-tijd (UTC).
        onderwerp: de titel van de afspraak.
        body_html: optionele HTML-inhoud.
        locatie: optionele locatie (weergavenaam).
        herinner_minuten: herinnering vooraf in minuten (0 = uit).

    Returns:
        Dict met ``id``, ``onderwerp`` en ``locatie``.

    Raises:
        ValueError: verplicht veld ontbreekt.
        RuntimeError: Graph geeft een fout.
    """
    if not onderwerp or not onderwerp.strip():
        raise ValueError("onderwerp is verplicht")
    if not start_iso or not eind_iso:
        raise ValueError("start_iso en eind_iso zijn verplicht")

    payload = _bouw_payload(start_iso, eind_iso, onderwerp, body_html, locatie,
                            herinner_minuten)
    resp = _client.post("/me/events", json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Afspraak aanmaken mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    data = resp.json()
    _log.info("Afspraak aangemaakt: %s", onderwerp)
    return {"id": data.get("id"), "onderwerp": onderwerp, "locatie": locatie}


def wijzig_afspraak(
    event_id: str,
    start_iso: str | None = None,
    eind_iso: str | None = None,
    onderwerp: str | None = None,
    body_html: str | None = None,
    locatie: str | None = None,
    herinner_minuten: int | None = None,
) -> dict[str, Any]:
    """Wijzig een bestaande afspraak. Alleen meegegeven velden worden aangepast.

    Args:
        event_id: id van de bestaande afspraak.
        Overige velden zijn optioneel; ``None`` = onveranderd laten.

    Returns:
        Dict met ``id`` en de gewijzigde velden.

    Raises:
        ValueError: ``event_id`` ontbreekt of er is niets om te wijzigen.
        RuntimeError: Graph geeft een fout.
    """
    if not event_id:
        raise ValueError("event_id is verplicht")

    payload: dict[str, Any] = {}
    if onderwerp is not None:
        payload["subject"] = onderwerp
    if body_html is not None:
        payload["body"] = {"contentType": "html", "content": body_html}
    if locatie is not None:
        payload["location"] = {"displayName": locatie}
    if start_iso is not None:
        payload["start"] = {"dateTime": _voor_graph(start_iso), "timeZone": "UTC"}
    if eind_iso is not None:
        payload["end"] = {"dateTime": _voor_graph(eind_iso), "timeZone": "UTC"}
    if herinner_minuten is not None:
        payload["isReminderOn"] = herinner_minuten > 0
        payload["reminderMinutesBeforeStart"] = herinner_minuten

    if not payload:
        raise ValueError("Niets om te wijzigen: geef minstens één veld mee")

    resp = _client.patch(f"/me/events/{event_id}", json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Afspraak wijzigen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    _log.info("Afspraak gewijzigd: %s", event_id)
    return {"id": event_id, **{k: v for k, v in {
        "onderwerp": onderwerp, "locatie": locatie}.items() if v is not None}}


def annuleer_afspraak(event_id: str) -> bool:
    """Verwijder een afspraak uit Outlook.

    Een afspraak die al weg is (``404``) telt ook als gelukt.

    Raises:
        ValueError: ``event_id`` ontbreekt.
        RuntimeError: Graph geeft een onverwachte fout.
    """
    if not event_id:
        raise ValueError("event_id is verplicht")

    resp = _client.delete(f"/me/events/{event_id}")
    if resp.status_code not in (200, 202, 204, 404):
        raise RuntimeError(
            f"Afspraak annuleren mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    _log.info("Afspraak geannuleerd: %s", event_id)
    return True


# ── Hulpjes ──────────────────────────────────────────────────────────────────


def _bouw_payload(start_iso, eind_iso, onderwerp, body_html, locatie,
                  herinner_minuten) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "subject": onderwerp,
        "start": {"dateTime": _voor_graph(start_iso), "timeZone": "UTC"},
        "end": {"dateTime": _voor_graph(eind_iso), "timeZone": "UTC"},
        "isReminderOn": herinner_minuten > 0,
        "reminderMinutesBeforeStart": herinner_minuten,
    }
    if body_html:
        payload["body"] = {"contentType": "html", "content": body_html}
    if locatie:
        payload["location"] = {"displayName": locatie}
    return payload


def _voor_graph(iso: str) -> str:
    """Maak een ISO-tijd geschikt voor het Graph-event-payload (zonder ``Z``;
    de tijdzone geven we apart als ``UTC`` mee)."""
    return iso.strip().rstrip("Z")


def _naar_utc_iso(dt_str: str) -> str:
    """Zorg dat een Graph-datetime een nette UTC-ISO is die op ``Z`` eindigt."""
    if not dt_str:
        return ""
    s = dt_str.strip()
    # Heeft al een tijdzone-aanduiding (Z of +/-offset achter de datum)?
    if s.endswith("Z") or "+" in s[10:] or "-" in s[10:]:
        return s
    if "." in s:  # microseconden inkorten tot 3 cijfers
        basis, micro = s.split(".", 1)
        s = f"{basis}.{micro[:3]}"
    return s + "Z"
