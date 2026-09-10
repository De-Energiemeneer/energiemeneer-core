"""Klant-velden die het aanmeldformulier en de portal delen: het factuuradres
en (sinds B1, 10-9-2026) het VvE-blok.

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

**VvE-blok (bouwplan intake-producten B1, beslissing 7):** bij een VvE-product is
de VvE de zakelijke opdrachtgever, met een bestuurslid of beheerder als
contactpersoon, en kan een beheerkantoor meedoen als Via-relatie (VvE blijft
opdrachtgever, beheerder in cc) of zelf als opdrachtgever. Dat landt op het
klantrecord als::

    klant["vve"] = {"vve_naam": …, "kvk": …, "contact_rol": "bestuur" | "beheerder",
                    "beheerder": {"naam": …, "email": …},
                    "beheerder_rol": "geen" | "via" | "opdrachtgever",
                    "kvk_naam_officieel": …,           # uit het Handelsregister (B2b), leeg = vrije invoer
                    "kvk_adres": {"straat": …, "huisnummer": …, "toevoeging": …,
                                  "postcode": …, "plaats": …}}

``vve_uit_formulier(data)`` leest dat blok tolerant (genest onder ``vve`` of plat
met ``vve_``-/``beheerder_``-voorvoegsels, zoals het formulier de velden stuurt);
``vve_ontbrekende_velden`` zegt wat er nog mist, zodat de portal het dossier op
"controleer handmatig" zet in plaats van stil verder te gaan.

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


# ── VvE-blok (B1, 10-9-2026) ────────────────────────────────────────────────

VVE = "vve"
VVE_VELDEN = ("vve_naam", "kvk", "contact_rol", "beheerder", "beheerder_rol",
              "kvk_naam_officieel", "kvk_adres")
CONTACT_ROLLEN = ("bestuur", "beheerder")
BEHEERDER_ROLLEN = ("geen", "via", "opdrachtgever")
BEHEERDER_VELDEN = ("naam", "email")
# Platte formulier-namen → veld in het blok.
VVE_FORMULIER_VELDEN = {"vve_naam": "vve_naam", "vve_kvk": "kvk", "vve_contact_rol": "contact_rol",
                        "vve_beheerder_rol": "beheerder_rol", "vve_kvk_naam_officieel": "kvk_naam_officieel"}
BEHEERDER_FORMULIER_VELDEN = {"naam": "beheerder_naam", "email": "beheerder_email"}

_ROL_SYNONIEMEN = {
    "bestuur": "bestuur", "bestuurslid": "bestuur", "bestuurder": "bestuur", "voorzitter": "bestuur",
    "beheerder": "beheerder", "beheer": "beheerder", "beheerkantoor": "beheerder",
    "geen": "geen", "nee": "geen", "none": "geen",   # leeg blijft leeg: dat meldt vve_ontbrekende_velden
    "via": "via", "contact": "via", "brengt in contact": "via",
    "opdrachtgever": "opdrachtgever", "zelf": "opdrachtgever",
}


def schoon_kvk(waarde) -> str:
    """KvK-nummer als acht cijfers (spaties/punten weg); iets anders → leeg,
    nooit een half nummer doorgeven."""
    cijfers = "".join(ch for ch in str(waarde or "") if ch.isdigit())
    return cijfers if len(cijfers) == 8 else ""


def _rol(waarde, toegestaan) -> str:
    w = _ROL_SYNONIEMEN.get(str(waarde or "").strip().lower(), "")
    return w if w in toegestaan else ""


def schoon_vve(blok) -> dict:
    """Normaliseer naar precies de VvE-velden (strings gestript, rollen op de
    vaste waarden, KvK acht cijfers, adres in de factuuradres-vorm)."""
    b = blok if isinstance(blok, dict) else {}
    beh = b.get("beheerder") if isinstance(b.get("beheerder"), dict) else {}
    beheerder_rol = _rol(b.get("beheerder_rol"), BEHEERDER_ROLLEN)
    contact_rol = _rol(b.get("contact_rol"), CONTACT_ROLLEN)
    return {
        "vve_naam": str(b.get("vve_naam") or "").strip(),
        "kvk": schoon_kvk(b.get("kvk")),
        "contact_rol": contact_rol,
        "beheerder": {k: str(beh.get(k) or "").strip() for k in BEHEERDER_VELDEN},
        "beheerder_rol": beheerder_rol,
        "kvk_naam_officieel": str(b.get("kvk_naam_officieel") or "").strip(),
        "kvk_adres": schoon_factuuradres(b.get("kvk_adres")),
    }


def heeft_vve(blok) -> bool:
    """True zodra er een VvE-naam of KvK-nummer in staat."""
    b = blok if isinstance(blok, dict) else {}
    return bool(str(b.get("vve_naam") or "").strip() or schoon_kvk(b.get("kvk")))


def vve_uit_formulier(data) -> dict | None:
    """Lees het VvE-blok uit intake-data, genest (``{"vve": {...}}``) of plat
    (``vve_naam``, ``vve_kvk``, ``vve_contact_rol``, ``beheerder_naam``,
    ``beheerder_email``, ``beheerder_rol``). Returnt het geschoonde blok, of
    None als de data er niets over zegt (particuliere aanvraag)."""
    d = data if isinstance(data, dict) else {}
    genest = d.get(VVE)
    if isinstance(genest, dict) and (heeft_vve(genest) or any(genest.get(k) for k in VVE_VELDEN)):
        return schoon_vve(genest)
    plat = {veld: d.get(naam) for naam, veld in VVE_FORMULIER_VELDEN.items()}
    plat["beheerder"] = {k: d.get(naam) for k, naam in BEHEERDER_FORMULIER_VELDEN.items()}
    if "beheerder_rol" in d:
        plat["beheerder_rol"] = d.get("beheerder_rol")
    if "beheerder_naam" in d or "beheerder_email" in d or any(
            str(v or "").strip() for k, v in plat.items() if k != "beheerder"):
        return schoon_vve(plat)
    return None


def vve_ontbrekende_velden(blok) -> list[str]:
    """Wat er nog mist voor een bruikbaar VvE-dossier, in vaste volgorde en in
    gewone taal (voor de logregel "controleer handmatig"). Regels: VvE-naam
    verplicht; contactrol verplicht; beheerder-rol verplicht; bij een
    beheerder-rol 'via' of 'opdrachtgever' zijn naam én e-mail van het
    beheerkantoor verplicht. Het KvK-nummer is optioneel (niet elke VvE is
    ingeschreven; B2b vult het aan uit het Handelsregister)."""
    b = schoon_vve(blok)
    mist = []
    if not b["vve_naam"]:
        mist.append("naam van de VvE")
    if not b["contact_rol"]:
        mist.append("rol van de contactpersoon (bestuur of beheerder)")
    if not b["beheerder_rol"]:
        mist.append("rol van de beheerder (geen, via of opdrachtgever)")
    elif b["beheerder_rol"] != "geen":
        if not b["beheerder"]["naam"]:
            mist.append("naam van het beheerkantoor")
        if not b["beheerder"]["email"]:
            mist.append("e-mailadres van het beheerkantoor")
    return mist


def normaliseer_vve(klant: dict) -> bool:
    """Zet ``klant["vve"]`` in de vaste vorm als het blok aanwezig is; een
    record zonder blok blijft ongemoeid (particuliere klant). Returnt True als
    er iets wijzigde."""
    if not isinstance(klant, dict) or VVE not in klant:
        return False
    oud = klant.get(VVE)
    nieuw = schoon_vve(oud)
    klant[VVE] = nieuw
    return oud != nieuw


def beheerder_is_opdrachtgever(klant) -> bool:
    """Beheerkantoor is zelf opdrachtgever (ontvangt offerte, OB en factuur)?"""
    k = klant if isinstance(klant, dict) else {}
    return schoon_vve(k.get(VVE))["beheerder_rol"] == "opdrachtgever"


def beheerder_in_cc(klant) -> bool:
    """Beheerkantoor als Via-relatie: VvE blijft opdrachtgever, beheerder in cc."""
    k = klant if isinstance(klant, dict) else {}
    return schoon_vve(k.get(VVE))["beheerder_rol"] == "via"
