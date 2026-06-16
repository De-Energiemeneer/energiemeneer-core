"""Voorgevel-oriëntatie van een pand bepalen (gevel-azimut).

Vervangt de fragiele één-methode-berekening uit ``admin-portal/voorbereiden.py``
(die op live-Overpass leunde en bij diepe rijtjeshuizen en gebogen hoekpanden ~90°
of tientallen graden mis kon zitten). De aanpak hier:

* **Drie onafhankelijke schatters** in plaats van één "waarheid":
  1. ``schat_straat_loodrecht`` — loodrecht op het dichtstbijzijnde stuk van de
     straat waar het adres op ligt (PDOK NWB, gefilterd op straatnaam). Robuust:
     lost de 90°-fout op, want de voorgevel staat vrijwel altijd evenwijdig aan de
     eigen straat. De VBO→straat-vector lost de 180°-ambiguïteit op.
  2. ``schat_footprint_rand`` — de buitennormaal van de footprint-rand die het
     meest evenwijdig aan de straat loopt én aan de straatzijde ligt. Precies bij
     onregelmatige panden. **Eerst filteren op straat-parallelliteit (graden),
     dán tie-breaken op afstand/straatkant (meters)** — graden en meters worden
     nooit in één score gemengd.
  3. ``schat_buren_mediaan`` — de circulaire mediaan van de oriëntaties van de
     buren in dezelfde straat. Vangnet voor een uitschieter in een rij.

* **Samenvoegen met een eerlijke confidence** (``combineer_schattingen``): vallen
  de schatters samen → hoge confidence, gebruiken. Lopen ze uiteen → lage
  confidence, dossier flaggen voor handmatige controle (sluit aan op de B7-flow)
  i.p.v. stil een foute waarde gebruiken.

Robuust-by-design: een hapering in één schatter of databron mag de berekening
nooit laten crashen; we vangen af, loggen, en vallen terug op een lagere-confidence
schatting of op "controle nodig".

Alle hoeken zijn kompasgraden (0=Noord, 90=Oost, ...), de buitennormaal van de
voorgevel (de richting waarin de gevel "kijkt"). Coördinaten zijn RD New (meter,
EPSG:28992).
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime
from typing import Any, Callable, Sequence

import requests

_log = logging.getLogger(__name__)

_USER_AGENT = "energiemeneer-core (https://de-energiemeneer.nl)"

# ── Toleranties (graden) ─────────────────────────────────────────────────────
# Een footprint-rand telt als "evenwijdig aan de straat" als hij hooguit zoveel
# graden van de straatrichting afwijkt (modulo 180°).
_PARALLEL_TOL = 30.0
# Twee schatters "zijn het eens" als ze hooguit zoveel graden verschillen → hoge
# confidence. Daarboven: de schatters spreken elkaar tegen → flaggen.
_CONSENSUS_TOL = 15.0
# Wijkt de gekozen hoek meer dan dit van de buren-mediaan af, dan is er iets mis:
# bij een tussenwoning de buren volgen, bij een hoekpand alleen flaggen.
_BUREN_AFWIJKING = 25.0


# ─── ISSO 8.3: hoek → windrichting ───────────────────────────────────────────

ISSO_RICHTINGEN: list[tuple[float, float, str]] = [
    (337.5, 360.0, "Noord"),
    (0.0,    22.4, "Noord"),
    (22.5,   67.4, "Noordoost"),
    (67.5,  112.4, "Oost"),
    (112.5, 157.4, "Zuidoost"),
    (157.5, 202.4, "Zuid"),
    (202.5, 247.4, "Zuidwest"),
    (247.5, 292.4, "West"),
    (292.5, 337.4, "Noordwest"),
]


def hoek_naar_isso(hoek: float) -> str:
    """Zet een kompashoek om naar de ISSO-8.3-windrichtingnaam."""
    hoek = hoek % 360
    for min_h, max_h, naam in ISSO_RICHTINGEN:
        if min_h <= hoek <= max_h:
            return naam
    return "Noord"


# ─── Circulaire wiskunde ─────────────────────────────────────────────────────
# Oriëntatie is circulaire data: 359° en 1° liggen 2° uit elkaar, niet 358°.
# Middelen mag dus NOOIT via een gewoon rekenkundig gemiddelde — altijd via
# eenheidsvectoren (cos/sin → atan2), anders ontstaat een fout rond 0/360°.

def _kompas(x1: float, y1: float, x2: float, y2: float) -> float:
    """Kompasrichting (0=Noord, 90=Oost) van segment (x1,y1)→(x2,y2)."""
    return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 360


def hoek_verschil(a: float, b: float) -> float:
    """Kleinste hoek tussen twee kompasrichtingen (0–180°)."""
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def circulair_gemiddelde(hoeken: Sequence[float]) -> float | None:
    """Circulair gemiddelde van kompashoeken via eenheidsvectoren."""
    hoeken = [h for h in hoeken if h is not None]
    if not hoeken:
        return None
    s = sum(math.sin(math.radians(h)) for h in hoeken)
    c = sum(math.cos(math.radians(h)) for h in hoeken)
    if abs(s) < 1e-9 and abs(c) < 1e-9:
        return None  # vectoren heffen elkaar op → geen zinnig gemiddelde
    return math.degrees(math.atan2(s, c)) % 360


def circulaire_mediaan(hoeken: Sequence[float]) -> float | None:
    """Circulaire mediaan: de waarde uit de set met de kleinste som van
    circulaire afstanden tot alle andere. Robuuster tegen uitschieters dan het
    gemiddelde (één fout pand in een rij trekt 'm niet scheef)."""
    hoeken = [h for h in hoeken if h is not None]
    if not hoeken:
        return None
    best, best_som = hoeken[0], float("inf")
    for kandidaat in hoeken:
        som = sum(hoek_verschil(kandidaat, h) for h in hoeken)
        if som < best_som:
            best_som, best = som, kandidaat
    return best % 360


# ─── Geometrie-helpers ───────────────────────────────────────────────────────

def _afstand_punt_segment(px, py, ax, ay, bx, by) -> float:
    """Kortste afstand van punt (px,py) tot lijnstuk (ax,ay)–(bx,by)."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _randen(contour: Sequence[tuple[float, float]]):
    """Itereer over de randen (opeenvolgende puntparen) van een contour."""
    for i in range(len(contour) - 1):
        (x1, y1), (x2, y2) = contour[i], contour[i + 1]
        yield i, x1, y1, x2, y2


def _centroide(contour: Sequence[tuple[float, float]]) -> tuple[float, float]:
    """Zwaartepunt van de contour (negeert het sluitpunt dat gelijk is aan het
    beginpunt)."""
    pts = contour[:-1] if len(contour) > 1 and contour[0] == contour[-1] else contour
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def _buitennormaal(seg_richting: float, mid: tuple[float, float],
                   richtpunt: tuple[float, float]) -> float:
    """Van de twee loodrechten op een segment: die welke naar ``richtpunt`` wijst
    (de straat, of het zwaartepunt-naar-buiten). Lost de 180°-ambiguïteit op."""
    a = (seg_richting + 90) % 360
    b = (seg_richting - 90) % 360
    naar = math.degrees(math.atan2(richtpunt[0] - mid[0], richtpunt[1] - mid[1])) % 360
    return a if hoek_verschil(a, naar) < hoek_verschil(b, naar) else b


def _dichtstbijzijnde_straat(vbo: tuple[float, float],
                             straat_segmenten: Sequence[tuple[float, float, float, float]]):
    """Geef (richting, midden, afstand) van het straatsegment het dichtst bij het
    VBO-punt, of None als er geen segmenten zijn."""
    px, py = vbo
    beste = None
    beste_d = float("inf")
    for (x1, y1, x2, y2) in straat_segmenten:
        d = _afstand_punt_segment(px, py, x1, y1, x2, y2)
        if d < beste_d:
            beste_d = d
            beste = (_kompas(x1, y1, x2, y2), ((x1 + x2) / 2, (y1 + y2) / 2), d)
    return beste


# ─── Schatter 1: loodrecht op de straat (robuust anker) ──────────────────────

def schat_straat_loodrecht(vbo: tuple[float, float],
                           straat_segmenten: Sequence[tuple[float, float, float, float]]
                           ) -> dict | None:
    """Voorgevel ⟂ op het dichtstbijzijnde stuk van de eigen straat, kijkend van
    het VBO naar de straat. Geeft None als er geen straatgeometrie is."""
    dichtst = _dichtstbijzijnde_straat(vbo, straat_segmenten)
    if dichtst is None:
        return None
    straat_richting, straat_mid, afstand = dichtst
    hoek = _buitennormaal(straat_richting, vbo, straat_mid)
    return {
        "methode": "straat-loodrecht",
        "hoek": round(hoek, 1),
        "straat_richting": round(straat_richting, 1),
        "afstand_straat_m": round(afstand, 1),
    }


# ─── Schatter 2: footprint-rand met straat-hint ──────────────────────────────

def schat_footprint_rand(contour: Sequence[tuple[float, float]],
                         vbo: tuple[float, float],
                         straat_segmenten: Sequence[tuple[float, float, float, float]] | None = None
                         ) -> dict | None:
    """Buitennormaal van de footprint-rand die de voorgevel is.

    Met straat-hint: filter eerst de randen die (binnen ``_PARALLEL_TOL`` graden)
    evenwijdig aan de straat lopen, kies daaruit met een tie-break op meters de
    rand aan de straatzijde die het dichtst bij het VBO ligt. **Graden en meters
    worden gescheiden gehouden** — geen gemengde score.

    Zonder bruikbare straat-hint: val terug op de footprint-rand het dichtst bij
    het VBO, met centroïde-correctie voor de buitenrichting.
    """
    if not contour or len(contour) < 3:
        return None
    px, py = vbo
    cx, cy = _centroide(contour)

    dichtst = _dichtstbijzijnde_straat(vbo, straat_segmenten) if straat_segmenten else None
    straat_richting = dichtst[0] if dichtst else None
    straat_mid = dichtst[1] if dichtst else None

    # Per rand: parallelliteit (graden), straatkant (ja/nee) en afstand (meters).
    randen = []
    for i, x1, y1, x2, y2 in _randen(contour):
        seg_r = _kompas(x1, y1, x2, y2)
        mid = ((x1 + x2) / 2, (y1 + y2) / 2)
        afstand = _afstand_punt_segment(px, py, x1, y1, x2, y2)
        if straat_richting is not None:
            par = min(hoek_verschil(seg_r, straat_richting),
                      hoek_verschil(seg_r, (straat_richting + 180) % 360))
            # Ligt het rand-midden aan dezelfde kant van het zwaartepunt als de straat?
            dot = (mid[0] - cx) * (straat_mid[0] - cx) + (mid[1] - cy) * (straat_mid[1] - cy)
            straatkant = dot > 0
        else:
            par, straatkant = None, True
        randen.append({"i": i, "seg_r": seg_r, "mid": mid, "afstand": afstand,
                       "par": par, "straatkant": straatkant})

    if straat_richting is not None:
        # Stap 1 (graden): houd alleen de straat-parallelle randen over.
        pool = [r for r in randen if r["par"] is not None and r["par"] <= _PARALLEL_TOL] or randen
        # Stap 2 (meters): straatzijde eerst, dan zo dicht mogelijk bij het VBO.
        straatzijde = [r for r in pool if r["straatkant"]] or pool
        keuze = min(straatzijde, key=lambda r: r["afstand"])
        richtpunt = straat_mid          # voorgevel kijkt naar de straat
    else:
        # Geen straat-hint: dichtstbijzijnde rand + centroïde-correctie.
        keuze = min(randen, key=lambda r: r["afstand"])
        richtpunt = keuze["mid"]        # zwaartepunt → rand = naar buiten
        # _buitennormaal verwacht een punt "buiten"; bij centroïde-correctie geven
        # we het rand-midden t.o.v. het zwaartepunt mee:
        richtpunt = (keuze["mid"][0] + (keuze["mid"][0] - cx),
                     keuze["mid"][1] + (keuze["mid"][1] - cy))

    hoek = _buitennormaal(keuze["seg_r"], keuze["mid"], richtpunt)
    return {
        "methode": "footprint-rand",
        "hoek": round(hoek, 1),
        "rand_index": keuze["i"],
        "afstand_m": round(keuze["afstand"], 1),
        "parallel_graden": None if keuze["par"] is None else round(keuze["par"], 1),
        "met_straat_hint": straat_richting is not None,
    }


# ─── Schatter 3: buren-mediaan (circulair) ───────────────────────────────────

def schat_buren_mediaan(buur_hoeken: Sequence[float]) -> dict | None:
    """Circulaire mediaan van de voorgevel-hoeken van de buren in dezelfde straat."""
    hoeken = [h for h in buur_hoeken if h is not None]
    if len(hoeken) < 2:
        return None
    mediaan = circulaire_mediaan(hoeken)
    if mediaan is None:
        return None
    return {
        "methode": "buren-mediaan",
        "hoek": round(mediaan, 1),
        "aantal_buren": len(hoeken),
    }


# ─── Hoekpand-detectie ───────────────────────────────────────────────────────

def is_hoekpand(contour: Sequence[tuple[float, float]],
                straat_namen_bij_pand: Sequence[str] | None = None) -> bool:
    """Grove hoekpand-detectie: het pand raakt meer dan één straat. Bij een
    hoekpand mag de buren-consensus de oriëntatie NIET overschrijven (de vrije
    zijgevel kijkt een andere kant op dan de rij)."""
    if straat_namen_bij_pand:
        unieke = {s.strip().lower() for s in straat_namen_bij_pand if s and s.strip()}
        if len(unieke) >= 2:
            return True
    return False


# ─── Samenvoegen tot één keuze + confidence ──────────────────────────────────

def combineer_schattingen(schattingen: Sequence[dict | None],
                          hoekpand: bool = False) -> dict:
    """Voeg de schatters samen tot één gekozen hoek + methode + confidence +
    alternatieven.

    Logica:
    * Footprint-rand én straat-loodrecht eens (≤ ``_CONSENSUS_TOL``) → hoge
      confidence; neem het circulaire gemiddelde (eventueel met een instemmende
      buren-mediaan erbij).
    * Ze spreken elkaar tegen → de straat-loodrechte is het robuuste anker, maar
      lage confidence: ``controle_nodig`` zodat het dossier in de B7-flow wordt
      geflagd.
    * Maar één schatter beschikbaar → midden-confidence (niet kruislings te
      controleren).
    * Buren-mediaan wijkt sterk af van de keuze: bij een tussenwoning de buren
      volgen, bij een hoekpand alleen flaggen.
    """
    geldig = {s["methode"]: s for s in schattingen if s and s.get("hoek") is not None}
    A = geldig.get("footprint-rand", {}).get("hoek")
    B = geldig.get("straat-loodrecht", {}).get("hoek")
    C = geldig.get("buren-mediaan", {}).get("hoek")

    alternatieven = [{"methode": s["methode"], "hoek": s["hoek"],
                      "naam": hoek_naar_isso(s["hoek"])}
                     for s in geldig.values()]

    if not geldig:
        return {
            "orientatie": "onbekend", "hoek_graden": None,
            "confidence": "geen", "controle_nodig": True,
            "methode": "geen schatting beschikbaar", "alternatieven": [],
        }

    spread = None
    if A is not None and B is not None:
        spread = hoek_verschil(A, B)
        if spread <= _CONSENSUS_TOL:
            instemmend = [A, B]
            if C is not None and hoek_verschil(C, B) <= _BUREN_AFWIJKING:
                instemmend.append(C)
            keuze = circulair_gemiddelde(instemmend)
            confidence, controle = "hoog", False
            methode = "footprint-rand + straat-loodrecht (eens)"
        else:
            keuze = B  # straat-loodrecht is het robuuste anker
            confidence, controle = "laag", True
            methode = "straat-loodrecht (footprint-rand wijkt af — controle nodig)"
    elif B is not None:
        keuze, confidence, controle = B, "midden", False
        methode = "straat-loodrecht (geen footprint)"
    elif A is not None:
        keuze, confidence, controle = A, "midden", False
        methode = "footprint-rand (geen straat-anker)"
    else:  # alleen buren
        keuze, confidence, controle = C, "laag", True
        methode = "buren-mediaan (geen eigen geometrie)"

    # Buren-correctie / hoekpand-vangnet.
    if C is not None and keuze is not None and hoek_verschil(keuze, C) > _BUREN_AFWIJKING:
        if hoekpand:
            controle = True
            methode += " · wijkt af van buren (hoekpand: niet overgenomen)"
        else:
            keuze = C
            confidence = "midden" if confidence == "hoog" else confidence
            controle = True
            methode += " · buren-correctie toegepast"

    if keuze is None:
        return {
            "orientatie": "onbekend", "hoek_graden": None,
            "confidence": "geen", "controle_nodig": True,
            "methode": methode, "alternatieven": alternatieven,
        }

    keuze = keuze % 360
    return {
        "orientatie": hoek_naar_isso(keuze),
        "hoek_graden": round(keuze, 1),
        "confidence": confidence,
        "controle_nodig": controle,
        "methode": methode,
        "spread_graden": None if spread is None else round(spread, 1),
        "hoekpand": hoekpand,
        "alternatieven": alternatieven,
    }


# ─── Live databronnen (PDOK Locatieserver, PDOK NWB, 3DBAG) ───────────────────
# Gescheiden van de pure rekenlogica hierboven zodat de tests met vaste fixtures
# kunnen draaien zonder echte HTTP. De orchestrator accepteert een eigen
# ``bronnen``-object (of kant-en-klare geometrie) — in tests injecteer je een fake.

def _haal_json(url: str, params: dict, timeout: int = 12) -> dict | None:
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": _USER_AGENT}, timeout=timeout)
        if r.status_code != 200:
            _log.warning("%s gaf HTTP %s", url, r.status_code)
            return None
        return r.json()
    except Exception as e:  # netwerk/timeout/parse — robuust-by-design
        _log.warning("Ophalen mislukt (%s): %s", url, e)
        return None


class LiveBronnen:
    """Standaard databronnen die echt online opvragen. Elk faalt zacht (None)."""

    _PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
    _NWB = "https://service.pdok.nl/rws/nwbwegen/wfs/v1_0"
    _DBAG = "https://api.3dbag.nl/collections/pand/items"

    def vbo_punt(self, straatnaam: str, huisnummer: str, woonplaats: str,
                 toevoeging: str = "") -> tuple[float, float] | None:
        """Officieel BAG-VBO-punt (RD) via PDOK Locatieserver."""
        q = " ".join(p for p in (straatnaam, str(huisnummer), toevoeging, woonplaats) if p)
        js = _haal_json(self._PDOK, {"q": q, "fq": "type:adres",
                                     "fl": "centroide_rd", "rows": 1})
        try:
            doc = js["response"]["docs"][0]
            m = re.match(r"POINT\(([\d.]+)\s+([\d.]+)\)", doc["centroide_rd"])
            return (float(m.group(1)), float(m.group(2)))
        except (TypeError, KeyError, IndexError, AttributeError):
            return None

    def straat_segmenten(self, straatnaam: str, punt: tuple[float, float],
                         straal_m: int = 180) -> list[tuple[float, float, float, float]]:
        """Segmenten van NWB-wegvakken met exact deze straatnaam, rond het punt
        (RD). Filteren op straatnaam is cruciaal voor hoekpanden — zo kiest de
        adres-straat welke gevel de voorgevel is."""
        x, y = punt
        bbox = f"{x - straal_m},{y - straal_m},{x + straal_m},{y + straal_m}"
        js = _haal_json(self._NWB, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeName": "nwbwegen:wegvakken", "outputFormat": "application/json",
            "srsName": "EPSG:28992", "bbox": f"{bbox},EPSG:28992", "count": 300,
        }, timeout=20)
        doel = (straatnaam or "").strip().lower()
        segs_op_naam: list = []
        segs_alle: list = []
        for f in (js or {}).get("features", []):
            naam = (f.get("properties", {}).get("sttNaam") or "").strip().lower()
            geom = f.get("geometry") or {}
            lijnen = (geom.get("coordinates", []) if geom.get("type") == "MultiLineString"
                      else [geom.get("coordinates", [])])
            for ln in lijnen:
                for i in range(len(ln) - 1):
                    seg = (ln[i][0], ln[i][1], ln[i + 1][0], ln[i + 1][1])
                    segs_alle.append(seg)
                    if naam == doel:
                        segs_op_naam.append(seg)
        # Op naam als het kan; anders alle nabije wegvakken als zwak vangnet.
        return segs_op_naam or segs_alle

    def pand_contour(self, pand_id: str,
                     punt: tuple[float, float] | None = None
                     ) -> list[tuple[float, float]] | None:
        """LoD0-footprint van het pand (RD). Met ``pand_id`` direct; anders het
        pand in de buurt van ``punt`` waarvan de footprint het punt bevat."""
        if pand_id:
            bag_id = pand_id if pand_id.startswith("NL.IMBAG") else f"NL.IMBAG.Pand.{pand_id}"
            js = _haal_json(f"{self._DBAG}/{bag_id}", {}, timeout=15)
            contour = _contour_uit_cityjson(js, bag_id) if js else None
            if contour:
                return contour
        if punt is not None:
            return self._contour_bij_punt(punt)
        return None

    def _contour_bij_punt(self, punt: tuple[float, float], straal_m: int = 30):
        x, y = punt
        bbox = f"{x - straal_m},{y - straal_m},{x + straal_m},{y + straal_m}"
        js = _haal_json(self._DBAG, {"bbox": bbox, "limit": 80}, timeout=25)
        if not js:
            return None
        beste, beste_d = None, float("inf")
        for feat in js.get("features", []):
            contour = _contour_uit_cityjson_feature(feat, js.get("metadata", {}))
            if not contour:
                continue
            if _punt_in_polygoon(x, y, contour):
                return contour
            d = min((_afstand_punt_segment(x, y, *e[1:]) for e in _randen(contour)),
                    default=float("inf"))
            if d < beste_d:
                beste_d, beste = d, contour
        return beste

    def buur_hoeken(self, straatnaam: str, huisnummer: str, woonplaats: str) -> list[float]:
        """Voorgevel-hoeken van de buren. Standaard leeg — de buren-consensus is
        optioneel en wordt door de caller (admin-portal) gevoed uit reeds bekende
        dossier-snapshots; live per-buur opvragen is te duur voor de hoofdflow."""
        return []


def _transform(metadata: dict):
    tr = (metadata or {}).get("transform", {})
    return tr.get("scale", [1, 1, 1]), tr.get("translate", [0, 0, 0])


def _contour_uit_cityjson_feature(feature: dict, metadata: dict):
    """LoD0-footprint uit één CityJSONFeature (vertices + boundaries)."""
    scale, translate = _transform(metadata)
    verts = [(v[0] * scale[0] + translate[0], v[1] * scale[1] + translate[1])
             for v in feature.get("vertices", [])]
    for obj in feature.get("CityObjects", {}).values():
        for g in obj.get("geometry", []):
            if str(g.get("lod", "")) == "0":
                b = g.get("boundaries", [])
                if b and b[0] and b[0][0]:
                    return [verts[i] for i in b[0][0]]
    return None


def _contour_uit_cityjson(js: dict, bag_id: str):
    """LoD0-footprint uit het single-item 3DBAG-antwoord."""
    feature = js.get("feature", {})
    metadata = js.get("metadata", {})
    # Het single-item antwoord nest CityObjects onder 'feature'; hergebruik dezelfde
    # parser door het in het feature-formaat te gieten.
    feature = {"vertices": feature.get("vertices", []),
               "CityObjects": feature.get("CityObjects", {})}
    return _contour_uit_cityjson_feature(feature, metadata)


def _punt_in_polygoon(px: float, py: float,
                      poly: Sequence[tuple[float, float]]) -> bool:
    """Ray-casting: ligt (px,py) binnen de (gesloten) polygoon?"""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > py) != (yj > py)) and \
           (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


# ─── Orchestrator: publieke API ──────────────────────────────────────────────

def bepaal_orientatie(straatnaam: str, huisnummer: str, woonplaats: str, *,
                      pand_id: str = "", toevoeging: str = "",
                      vbo: tuple[float, float] | None = None,
                      contour: Sequence[tuple[float, float]] | None = None,
                      straat_segmenten: Sequence | None = None,
                      buur_hoeken: Sequence[float] | None = None,
                      straat_namen_bij_pand: Sequence[str] | None = None,
                      bronnen: Any | None = None) -> dict:
    """Bepaal de voorgevel-oriëntatie met drie schatters + confidence.

    Geometrie kan kant-en-klaar worden meegegeven (``vbo``, ``contour``,
    ``straat_segmenten``, ``buur_hoeken``) — dat is wat de tests doen, zonder
    HTTP. Ontbreekt iets, dan wordt het via ``bronnen`` (standaard ``LiveBronnen``)
    opgehaald. Elke stap faalt zacht: een hapering blokkeert het dossier nooit.

    Returnt een dict met o.a. ``orientatie`` (ISSO-naam), ``hoek_graden``,
    ``confidence`` (hoog/midden/laag/geen), ``controle_nodig`` (bool, → B7-flag),
    ``methode``, ``alternatieven`` en ``bron``/``tijdstip`` voor de BRL-momentopname.
    """
    bronnen = bronnen or LiveBronnen()

    def _veilig(naam, fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            _log.warning("Oriëntatie-stap %s mislukt: %s", naam, e)
            return None

    if vbo is None:
        vbo = _veilig("vbo_punt", bronnen.vbo_punt, straatnaam, huisnummer,
                      woonplaats, toevoeging)
    if vbo is None:
        return {"orientatie": "onbekend", "hoek_graden": None, "confidence": "geen",
                "controle_nodig": True, "methode": "adrespunt niet gevonden",
                "alternatieven": [], "bron": "PDOK/NWB/3DBAG",
                "tijdstip": datetime.now().strftime("%d-%m-%Y %H:%M")}

    if straat_segmenten is None:
        straat_segmenten = _veilig("straat_segmenten", bronnen.straat_segmenten,
                                   straatnaam, vbo) or []
    if contour is None:
        contour = _veilig("pand_contour", bronnen.pand_contour, pand_id, vbo)
    if buur_hoeken is None:
        buur_hoeken = _veilig("buur_hoeken", bronnen.buur_hoeken,
                              straatnaam, huisnummer, woonplaats) or []

    schattingen = [
        _veilig("straat_loodrecht", schat_straat_loodrecht, vbo, straat_segmenten),
        _veilig("footprint_rand", schat_footprint_rand, contour, vbo, straat_segmenten),
        _veilig("buren_mediaan", schat_buren_mediaan, buur_hoeken),
    ]
    hoekpand = _veilig("is_hoekpand", is_hoekpand, contour or [], straat_namen_bij_pand) or False

    resultaat = combineer_schattingen(schattingen, hoekpand=hoekpand)
    resultaat["lat"], resultaat["lon"] = None, None
    resultaat["bron"] = "PDOK Locatieserver (VBO) + PDOK NWB (straat) + 3DBAG (footprint)"
    resultaat["isso_tabel"] = "ISSO 8.3"
    resultaat["tijdstip"] = datetime.now().strftime("%d-%m-%Y %H:%M")
    return resultaat
