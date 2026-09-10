"""Productcatalogus: de enige lijst van producten die het aanmeldformulier en
de portal delen, met per product het profiel dat bepaalt hoe de keten ermee
omgaat (bouwplan intake-producten, stap A1, 9-9-2026).

Waarom hier: de productnaam is de sleutel voor SnelStart-artikelen,
OB-sjablonen, automaat-scope, bijlagen, mappenboom en straks de slotduur en
het zelf inplannen. Tot 9-9 stond die lijst op drie plekken (bord.py,
aanvragen.py, bord.html) en zat productgedrag als losse tuples en
"vve"-substring-checks door de portal heen. Vanaf nu leest alles hier.

De profielwaarden spiegelen het gedrag van de portal op 9-9-2026 exact
(byte-gelijk voor het energielabel); nieuwe mogelijkheden (VvE-prijstak,
dossiertype vve_scan, automaat voor de VvE-scan) worden hier later omgezet,
niet in losse if-ketens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    """Eén product met zijn profiel. Alle velden zijn gedrag, geen tekst."""

    naam: str                  # portal-/SnelStart-naam, bv. "Energielabel Advies"
    slug: str                  # URL-/formulierwaarde, bv. "energielabel-advies"
    kort: str                  # kort label voor chips/tegels
    doelgroep: str             # "particulier" | "vve" | "onbekend"
    automaat: bool             # lead-automaat mag dit product zelfstandig doorlopen
    offerteregels: str         # "woning" (m²-staffel + productartikelen) | "vve" (vast tarief per complex) | "geen"
    bijlage_g: bool            # Bijlage G mee met de opdrachtbevestiging (labelopname)
    ob_sjabloon: str           # Mailteksten-template-id voor de opdrachtbevestiging
    afspraak_vereist: bool     # eindcontrole eist een geboekte afspraak vóór de OB
    facturatie: str            # "robot" (hele offerte → factuur) | "termijnen" | "handmatig"
    dossiertype: str           # "particulier" | "vve_maatwerk" | "vve_scan"
    boom: str                  # dossiermap-boom: "labels" | "adviezen" | "vve" | "beide"
    koepel: bool               # mag via de koepel-upload (EnergielabelPortaal)
    zelf_inplannen: bool       # klant mag zelf een slot kiezen op /bevestig
    duur_minuten: int | None   # startwaarde afspraakduur; None = algemene slot-instelling
    # B1 (10-9-2026): nieuwe velden voor de Energiescan VvE. Voor de bestaande
    # producten spiegelen ze het gedrag van 9-9 (niets verandert).
    ob_automatisch: bool = True    # automaat mag de OB zelf versturen; False = alleen klaarzetten
    woning_eisen: bool = True      # eindcontrole eist woninggegevens (m², bouwjaar, EP); VvE niet
    agenda_titel: str = "Energielabel opname"   # het vaste woord in de agenda-titel ("Naam: <titel> …")


ONBEKEND = "Nog te bepalen"

CATALOGUS: tuple[Product, ...] = (
    Product("Energielabel", "energielabel", "Energielabel", "particulier",
            automaat=True, offerteregels="woning", bijlage_g=True,
            ob_sjabloon="opdrachtbevestiging_energielabel", afspraak_vereist=True,
            facturatie="robot", dossiertype="particulier", boom="labels", koepel=True,
            zelf_inplannen=True, duur_minuten=90),
    Product("Herlabellen na advies", "herlabellen", "Herlabel", "particulier",
            automaat=False, offerteregels="geen", bijlage_g=False,
            ob_sjabloon="opdrachtbevestiging_herlabellen", afspraak_vereist=True,
            facturatie="robot", dossiertype="particulier", boom="labels", koepel=True,
            zelf_inplannen=False, duur_minuten=None),
    Product("Energielabel Advies", "energielabel-advies", "Label Advies", "particulier",
            automaat=True, offerteregels="woning", bijlage_g=True,
            ob_sjabloon="opdrachtbevestiging_energielabel_advies", afspraak_vereist=True,
            facturatie="robot", dossiertype="particulier", boom="labels", koepel=True,
            zelf_inplannen=True, duur_minuten=90),
    Product("Maatwerkadvies particulier", "maatwerkadvies", "Maatwerk part.", "particulier",
            automaat=True, offerteregels="woning", bijlage_g=False,
            ob_sjabloon="offerte_maatwerk_particulier", afspraak_vereist=True,
            facturatie="termijnen", dossiertype="particulier", boom="adviezen", koepel=True,
            zelf_inplannen=True, duur_minuten=120),
    # B1 (10-9-2026, beslissingen 3, 4, 6, 7): de VvE-scan loopt door de automaat
    # met de VvE-prijstak (vast tarief vanaf 8 woonfuncties), eigen dossiertype,
    # map onder de VvE-basis, eindcontrole zonder woning-eisen maar mét het
    # geboekte bezoek (180 min), en de OB wordt eerst alleen klaargezet.
    Product("Energiescan VvE", "energiescan-vve", "Scan VvE", "vve",
            automaat=True, offerteregels="vve", bijlage_g=False,
            ob_sjabloon="offerte_energiescan_vve", afspraak_vereist=True,
            facturatie="robot", dossiertype="vve_scan", boom="vve", koepel=False,
            zelf_inplannen=True, duur_minuten=180,
            ob_automatisch=False, woning_eisen=False, agenda_titel="Energiescan VvE bezoek"),
    Product("Maatwerkadvies VvE", "maatwerkadvies-vve", "Maatwerk VvE", "vve",
            automaat=False, offerteregels="geen", bijlage_g=False,
            ob_sjabloon="offerte_maatwerk_vve", afspraak_vereist=True,
            facturatie="termijnen", dossiertype="vve_maatwerk", boom="vve", koepel=False,
            zelf_inplannen=False, duur_minuten=None,
            woning_eisen=False, agenda_titel="Maatwerkadvies VvE bezoek"),
    Product(ONBEKEND, "nog-te-bepalen", "Nog te bepalen", "onbekend",
            automaat=False, offerteregels="geen", bijlage_g=False,
            ob_sjabloon="opdrachtbevestiging_generiek", afspraak_vereist=True,
            facturatie="handmatig", dossiertype="particulier", boom="beide", koepel=True,
            zelf_inplannen=False, duur_minuten=None),
)

_OP_NAAM = {p.naam.lower(): p for p in CATALOGUS}
_OP_SLUG = {p.slug: p for p in CATALOGUS}


def alle() -> tuple[Product, ...]:
    """Alle producten in catalogusvolgorde (= de volgorde in dropdowns)."""
    return CATALOGUS


def namen() -> tuple[str, ...]:
    """Alle productnamen in catalogusvolgorde."""
    return tuple(p.naam for p in CATALOGUS)


def vind(naam: str | None) -> Product | None:
    """Product op exacte naam (hoofdletter- en spatie-tolerant), anders None."""
    return _OP_NAAM.get(str(naam or "").strip().lower())


def is_bekend(naam: str | None) -> bool:
    return vind(naam) is not None


def profiel(naam: str | None) -> Product:
    """Het profiel van een product; onbekend of leeg → het profiel van
    :data:`ONBEKEND` (nooit stil een energielabel-profiel)."""
    return vind(naam) or _OP_NAAM[ONBEKEND.lower()]


def van_slug(slug: str | None) -> Product | None:
    """Product op slug (formulier/URL), anders None."""
    return _OP_SLUG.get(str(slug or "").strip().lower())


def is_vve(naam: str | None) -> bool:
    """VvE-product? Via het profiel; voor een naam buiten de catalogus geldt de
    oude substring-regel ("vve" in de naam) zodat historische dossiers niet
    stil van kant wisselen."""
    p = vind(naam)
    if p is not None:
        return p.doelgroep == "vve"
    return "vve" in str(naam or "").lower()


def namen_met(**eisen) -> tuple[str, ...]:
    """Productnamen waarvan het profiel aan alle eisen voldoet, in
    catalogusvolgorde. Bijvoorbeeld ``namen_met(automaat=True)``.
    Een onbekend veld is een programmeerfout en geeft AttributeError."""
    uit = []
    for p in CATALOGUS:
        if all(getattr(p, veld) == waarde for veld, waarde in eisen.items()):
            uit.append(p.naam)
    return tuple(uit)
