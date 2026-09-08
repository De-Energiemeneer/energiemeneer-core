"""Klant-velden die het aanmeldformulier en de portal delen: het factuuradres.

Eén definitie (principe 1, één keer invoeren). Het aanmeldformulier op de
website is de bron van de veldnamen: de invoervelden ``factuur-straat``,
``factuur-huisnummer``, ``factuur-toevoeging``, ``factuur-postcode`` en
``factuur-plaats`` landen op het klantrecord als::

    klant["factuuradres_afwijkend"] = True | False
    klant["factuuradres"] = {"straat": …, "huisnummer": …, "toevoeging": …,
                             "postcode": …, "plaats": …}

Dezelfde vorm als het adresdeel van ``klant["bedrijf"]`` en van
``relatie["factuuradres"]`` in de portal, dus geen nieuwe sleutels om te
onthouden. Het factuuradres staat los van het factuurtype: zowel een
particuliere als een zakelijke klant kan een afwijkend factuuradres hebben.

``factuuradres_van(klant, woonadres)`` is vanaf nu de enige plek waar de keuze
"factuuradres of woonadres" wordt gemaakt. Het woonadres is het objectadres van
het dossier (de sleutels straatnaam/huisnummer/huisletter/toevoeging/postcode/
woonplaats) en het resultaat gebruikt diezelfde sleutels, zodat SnelStart-robot,
invoerkaart en Vabi-invuller er direct mee overweg kunnen.
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)

# Sleutels op het klantrecord.
FACTUURADRES_AFWIJKEND = "factuuradres_afwijkend"
FACTUURADRES = "factuuradres"

# De adresvelden, exact de formulier-ids zonder het 'factuur-'-voorvoegsel.
FACTUURADRES_VELDEN = ("straat", "huisnummer", "toevoeging", "postcode", "plaats")
# Verplicht zodra 'afwijkend' aan staat (toevoeging mag leeg).
FACTUURADRES_VERPLICHT = ("straat", "huisnummer", "postcode", "plaats")

# De platte formulier-namen (``factuur-straat`` → ``factuur_straat``), voor het
# geval de intake ze plat aanlevert in plaats van als genest dict.
FORMULIER_VELDEN = {v: f"factuur_{v}" for v in FACTUURADRES_VELDEN}

_WAAR = ("1", "true", "ja", "yes", "on", "ander", "afwijkend")


def naar_bool(waarde) -> bool:
    """Tolerante bool-lezer voor de checkbox (JSON true, '1', 'ja', 'on', …)."""
    if isinstance(waarde, bool):
        return waarde
    if waarde is None:
        return False
    if isinstance(waarde, (int, float)):
        return waarde != 0
    return str(waarde).strip().lower() in _WAAR


def schoon_factuuradres(adres) -> dict:
    """Normaliseer naar precies de vijf velden (strings, gestript; rest weg)."""
    a = adres if isinstance(adres, dict) else {}
    uit = {k: str(a.get(k, "") or "").strip() for k in FACTUURADRES_VELDEN}
    uit["postcode"] = uit["postcode"].replace(" ", "").upper()
    return uit


def heeft_factuuradres(adres) -> bool:
    """True zodra er iets van een adres in staat (straat, huisnummer of postcode)."""
    a = adres if isinstance(adres, dict) else {}
    return any(str(a.get(k) or "").strip() for k in ("straat", "huisnummer", "postcode"))


def ontbrekende_velden(adres) -> list[str]:
    """De verplichte velden die (nog) leeg zijn, in vaste volgorde."""
    a = adres if isinstance(adres, dict) else {}
    return [k for k in FACTUURADRES_VERPLICHT if not str(a.get(k) or "").strip()]


def _effectief(klant) -> dict:
    """Kopie van het klantrecord met de factuuradres-sleutels gegarandeerd
    aanwezig. Een dict zónder vlag (record van vóór de migratie, of een
    tijdelijk dict zoals het relatie-pad van de SnelStart-robot) krijgt
    dezelfde afleiding als ``normaliseer`` — het origineel blijft ongemoeid."""
    k = dict(klant) if isinstance(klant, dict) else {}
    if FACTUURADRES_AFWIJKEND not in k:
        normaliseer(k)
    return k


def is_afwijkend(klant) -> bool:
    return naar_bool(_effectief(klant).get(FACTUURADRES_AFWIJKEND))


def uit_formulier(data) -> tuple[bool | None, dict]:
    """Lees checkbox + adres uit intake-data, in elke vorm die het formulier of de
    portal kan sturen:

    - genest: ``{"factuuradres_afwijkend": true, "factuuradres": {...}}``
    - plat:   ``{"factuur_straat": …, "factuur_postcode": …}`` (de formulier-ids)
    - de radio ``factuur_type == "ander"`` telt als 'afwijkend aan'.

    Returnt ``(afwijkend, adres)``; ``afwijkend`` is None als de data er niets
    over zegt (dan beslist de aanroeper, bv. via ``normaliseer``).
    """
    d = data if isinstance(data, dict) else {}
    adres = schoon_factuuradres(d.get(FACTUURADRES))
    if not heeft_factuuradres(adres):
        plat = {v: d.get(naam) for v, naam in FORMULIER_VELDEN.items()}
        if any(str(x or "").strip() for x in plat.values()):
            adres = schoon_factuuradres(plat)
    afwijkend: bool | None
    if FACTUURADRES_AFWIJKEND in d:
        afwijkend = naar_bool(d.get(FACTUURADRES_AFWIJKEND))
    elif str(d.get("factuur_type") or "").strip().lower() == "ander":
        afwijkend = True
    elif heeft_factuuradres(adres):
        afwijkend = True
    else:
        afwijkend = None
    return afwijkend, adres


def normaliseer(klant: dict) -> bool:
    """Zet de twee sleutels op een klantrecord; idempotent.

    Ontbreekt de vlag nog (record van vóór deze velden, of een intake die er
    niets over zegt) en staat er een gevuld adres in ``klant["bedrijf"]`` (het
    oude zakelijke factuuradres), dan wordt dat het factuuradres met
    ``afwijkend = True`` zodat niets verloren gaat. Staat de vlag er al, dan
    worden alleen de typen rechtgetrokken. Returnt True als er iets wijzigde.
    """
    if not isinstance(klant, dict):
        return False
    oud_vlag = klant.get(FACTUURADRES_AFWIJKEND)
    oud_adres = klant.get(FACTUURADRES)
    adres = schoon_factuuradres(oud_adres)
    if FACTUURADRES_AFWIJKEND in klant:
        vlag = naar_bool(oud_vlag)
    else:
        bedrijf_adres = schoon_factuuradres(klant.get("bedrijf"))
        if not heeft_factuuradres(adres) and heeft_factuuradres(bedrijf_adres):
            adres = bedrijf_adres
        vlag = heeft_factuuradres(adres)
    gewijzigd = (oud_vlag is not vlag) or (oud_adres != adres)
    klant[FACTUURADRES_AFWIJKEND] = vlag
    klant[FACTUURADRES] = adres
    return gewijzigd


def _naar_woonadres_vorm(adres: dict) -> dict:
    """Formulier-vorm (straat/plaats) → objectadres-sleutels (straatnaam/woonplaats)."""
    a = schoon_factuuradres(adres)
    return {"straatnaam": a["straat"], "huisnummer": a["huisnummer"], "huisletter": "",
            "toevoeging": a["toevoeging"], "postcode": a["postcode"], "woonplaats": a["plaats"]}


def factuuradres_van(klant, woonadres) -> dict:
    """Hét factuuradres van een klant: het afwijkende factuuradres als de
    checkbox aan staat én er een adres is ingevuld, anders het woonadres
    (objectadres). Resultaat in objectadres-sleutels plus ``bron``:
    ``"factuuradres"`` of ``"woonadres"``.
    """
    k = _effectief(klant)
    if naar_bool(k.get(FACTUURADRES_AFWIJKEND)) and heeft_factuuradres(k.get(FACTUURADRES)):
        return {**_naar_woonadres_vorm(k.get(FACTUURADRES)), "bron": "factuuradres"}
    w = woonadres if isinstance(woonadres, dict) else {}
    return {"straatnaam": str(w.get("straatnaam") or ""), "huisnummer": str(w.get("huisnummer") or ""),
            "huisletter": str(w.get("huisletter") or ""), "toevoeging": str(w.get("toevoeging") or ""),
            "postcode": str(w.get("postcode") or ""), "woonplaats": str(w.get("woonplaats") or ""),
            "bron": "woonadres"}


def adresregel(adres) -> str:
    """Platte weergave van een adres in objectadres-sleutels:
    ``"Straat 5 A, 1234AB Plaats"`` (lege delen weggelaten)."""
    a = adres if isinstance(adres, dict) else {}
    nummer = "".join(str(a.get(k) or "").strip() for k in ("huisnummer", "huisletter"))
    regel = " ".join(x for x in (str(a.get("straatnaam") or "").strip(), nummer,
                                 str(a.get("toevoeging") or "").strip()) if x)
    pc_plaats = " ".join(x for x in (str(a.get("postcode") or "").strip(),
                                     str(a.get("woonplaats") or "").strip()) if x)
    return ", ".join(x for x in (regel, pc_plaats) if x)


def factuuradres_regel(klant, woonadres) -> str:
    """``adresregel(factuuradres_van(klant, woonadres))`` in één stap."""
    return adresregel(factuuradres_van(klant, woonadres))
