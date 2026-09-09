"""De vaste Energiemeneer-opmaak voor opname-afspraken — het "merk".

Bron: ``admin-portal/admin-portal/ms_graph.py`` (``_bouw_event_body``, de
schoonste opmaak). In de oude tools zat die opmaak vastgebakken in de agenda-
code; hier leeft ze losgekoppeld op één plek, zodat een wijziging aan titel of
body maar op één plaats hoeft.

Dit zijn **pure functies**: geen Graph-aanroepen, geen token. Je geeft klant- en
adresgegevens, je krijgt titel + HTML-body + locatie terug. Die geef je door aan
:func:`energiemeneer_core.graph_api.agenda.maak_afspraak`. Zo weet de agenda-laag
*hoe* je een afspraak maakt en deze module *wat* erin staat.

Vaste afspraken (Meesterbrein H9.3): duur 90 minuten, herinnering 60 minuten
vooraf. De titel toont klantnaam, oppervlakte en de begin-/eindtijd (Amsterdamse
tijd). De body toont de klant-, adres- en dossiergegevens.

Zie BOUWPLAN.md, Module 7.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

_log = logging.getLogger(__name__)

# Vaste waarden uit het contract (Meesterbrein H9.3).
DUUR_MINUTEN = 90
HERINNERING_MINUTEN = 60

_AMS_ZONE: ZoneInfo | None = None


def opmaak_opname(
    start_iso: str,
    eind_iso: str,
    klant: dict[str, Any] | None = None,
    adres: dict[str, Any] | None = None,
    woningtype: str = "",
    prijs: str = "",
    label: str = "",
    makelaar: str = "",
) -> dict[str, Any]:
    """Bouw de vaste opmaak (titel, body, locatie) voor een opname-afspraak.

    Args:
        start_iso, eind_iso: begin/eind als UTC-ISO (zoals de agenda-module ze
            ook gebruikt). De tijden in de titel worden naar Amsterdamse tijd
            omgerekend.
        klant: dict met ``voornaam``, ``achternaam``, ``email``, ``telefoon``,
            ``opmerkingen`` en optioneel ``bedrijf`` (``{naam, kvk, btw}``).
        adres: dict met ``straatnaam``, ``huisnummer``, ``huisletter``,
            ``toevoeging``, ``postcode``, ``woonplaats``, ``oppervlakte``,
            ``bouwjaar`` en optioneel ``label``.
        woningtype: type woning (bijv. ``"Tussenwoning"``).
        prijs: prijs als tekst of getal (bijv. ``"315"``).
        label: huidig energielabel; valt terug op ``adres["label"]``.
        makelaar: naam van de makelaar; alleen getoond als ingevuld.

    Returns:
        Dict met ``onderwerp``, ``body_html``, ``locatie`` en
        ``herinner_minuten`` — precies wat
        :func:`energiemeneer_core.graph_api.agenda.maak_afspraak` verwacht.

    Raises:
        ValueError: start- of eindtijd ontbreekt of is onleesbaar.
        RuntimeError: de tijdzone 'Europe/Amsterdam' is niet beschikbaar.
    """
    if not start_iso or not eind_iso:
        raise ValueError("start_iso en eind_iso zijn verplicht")

    klant = klant or {}
    adres = adres or {}

    t1 = _amsterdam_hhmm(start_iso)
    t2 = _amsterdam_hhmm(eind_iso)

    klant_naam = _volledige_naam(klant)
    opp = adres.get("oppervlakte")
    opp_str = f" {opp}m²" if opp else ""
    onderwerp = f"{klant_naam}: Energielabel opname{opp_str} tussen {t1} en {t2} uur"

    locatie = _locatie(adres)
    body_html = _body(klant, adres, woningtype, prijs, label, makelaar, klant_naam)

    _log.info("Opname-opmaak gebouwd: %s", onderwerp)
    return {
        "onderwerp": onderwerp,
        "body_html": body_html,
        "locatie": locatie,
        "herinner_minuten": HERINNERING_MINUTEN,
    }


def bereken_eindtijd(start_iso: str) -> str:
    """Geef de standaard-eindtijd: begin + 90 minuten, als UTC-ISO (op ``Z``).

    Handig zodat de vaste opname-duur uit het contract maar op één plek leeft.

    Raises:
        ValueError: starttijd ontbreekt of is onleesbaar.
    """
    if not start_iso:
        raise ValueError("start_iso is verplicht")
    eind = _parse_utc(start_iso) + timedelta(minutes=DUUR_MINUTEN)
    return eind.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Tijd-hulpjes ─────────────────────────────────────────────────────────────


def _ams_zone() -> ZoneInfo:
    global _AMS_ZONE
    if _AMS_ZONE is None:
        try:
            _AMS_ZONE = ZoneInfo("Europe/Amsterdam")
        except Exception as e:  # zoneinfo-data ontbreekt
            raise RuntimeError(
                "Tijdzone 'Europe/Amsterdam' niet beschikbaar — installeer het "
                "'tzdata'-pakket (pip install tzdata)."
            ) from e
    return _AMS_ZONE


def _parse_utc(iso: str) -> datetime:
    """Lees een UTC-ISO-tijd in als een tijdzone-bewuste datetime."""
    s = iso.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"Onleesbare tijd: {iso}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _amsterdam_hhmm(iso: str) -> str:
    """Zet een UTC-ISO-tijd om naar Amsterdamse ``HH:MM`` (met zomertijd)."""
    return _parse_utc(iso).astimezone(_ams_zone()).strftime("%H:%M")


# ── Opmaak-hulpjes ───────────────────────────────────────────────────────────


def _volledige_naam(klant: dict[str, Any]) -> str:
    voornaam = (klant.get("voornaam") or "").strip()
    achternaam = (klant.get("achternaam") or "").strip()
    return f"{voornaam} {achternaam}".strip() or "Klant onbekend"


def _huisnummer_volledig(adres: dict[str, Any]) -> str:
    hn = str(adres.get("huisnummer") or "").strip()
    hl = (adres.get("huisletter") or "").strip()
    toev = (adres.get("toevoeging") or "").strip()
    return f"{hn}{hl}" + (f"-{toev}" if toev else "")


def _locatie(adres: dict[str, Any]) -> str:
    straat = (adres.get("straatnaam") or "").strip()
    huisn = _huisnummer_volledig(adres)
    pc = (adres.get("postcode") or "").strip()
    wp = (adres.get("woonplaats") or "").strip()
    return f"{straat} {huisn}, {pc} {wp}".strip(", ").strip()


def _e(waarde: Any) -> str:
    """Maak een waarde HTML-veilig (voor in de body)."""
    return html.escape(str(waarde))


def _body(
    klant: dict[str, Any],
    adres: dict[str, Any],
    woningtype: str,
    prijs: str,
    label: str,
    makelaar: str,
    klant_naam: str,
) -> str:
    email = (klant.get("email") or "").strip()
    telefoon = (klant.get("telefoon") or "").strip()
    opmerking = (klant.get("opmerkingen") or "").strip()
    bedrijf = klant.get("bedrijf")

    straat = (adres.get("straatnaam") or "").strip()
    huisn = _huisnummer_volledig(adres)
    pc = (adres.get("postcode") or "").strip()
    wp = (adres.get("woonplaats") or "").strip()
    bouwjaar = adres.get("bouwjaar") or "—"
    opp = adres.get("oppervlakte") or "—"
    label_str = label or adres.get("label") or "onbekend"
    woningtype_str = (woningtype or "—").capitalize()
    prijs_str = f"€{prijs}" if prijs else "—"

    makelaar_blok = ""
    if makelaar and makelaar.strip():
        makelaar_blok = f"<br><br><b>Makelaar:</b><br>{_e(makelaar.strip())}"

    bedrijf_blok = ""
    if isinstance(bedrijf, dict) and (bedrijf.get("naam") or "").strip():
        regels = [_e(bedrijf["naam"])]
        if (bedrijf.get("kvk") or "").strip():
            regels.append("KvK: " + _e(bedrijf["kvk"]))
        if (bedrijf.get("btw") or "").strip():
            regels.append("BTW: " + _e(bedrijf["btw"]))
        bedrijf_blok = "<br><br><b>— Zakelijk —</b><br>" + "<br>".join(regels)

    opmerking_blok = ""
    if opmerking:
        opmerking_blok = f"<br><br><b>Opmerking:</b><br>{_e(opmerking)}"

    return (
        "<html><body>\n"
        '<p style="font-family:Calibri,Arial,sans-serif;font-size:11pt;line-height:1.8">\n'
        f"<b>{_e(klant_naam)}</b><br>\n"
        f'{_e(email) or "—"}<br>\n'
        f'{_e(telefoon) or "—"}<br>\n'
        "<br>\n"
        f"<b>{_e(straat)} {_e(huisn)}</b><br>\n"
        f"{_e(pc)} {_e(wp)}<br>\n"
        "<br>\n"
        f"Bouwjaar: {_e(bouwjaar)} &nbsp;|&nbsp; Oppervlakte: {_e(opp)} m² "
        f"&nbsp;|&nbsp; Huidig label: <b>{_e(label_str)}</b><br>\n"
        f"Woningtype: {_e(woningtype_str)} &nbsp;|&nbsp; Prijs: {_e(prijs_str)}"
        f"{makelaar_blok}{bedrijf_blok}{opmerking_blok}\n"
        "</p>\n"
        "</body></html>"
    )
