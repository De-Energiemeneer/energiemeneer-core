"""Tests voor de voorgevel-oriëntatie (energiemeneer_core.orientatie).

Twee soorten tests:

* **Pure-logica-tests** op de circulaire wiskunde en de losse schatters — snel en
  zonder data.
* **Regressietests** op drie handmatig gecontroleerde, eerder fout berekende
  adressen. De échte footprint- en straatgeometrie is éénmalig live opgehaald en
  ingevroren in ``tests/fixtures/orientatie_panden.json`` — zo draaien deze tests
  deterministisch zonder live HTTP (conform de projectregel: externe calls mocken).

De drie ijkpunten (door Kevin handmatig gecontroleerd):
* Hendrick de Keyserstraat 68, Utrecht — moet ~209,3° (was fout: 299,6°)
* Hendrick de Keyserstraat 66, Utrecht — zelfde rij, zelfde fout
* Stadhouderslaan 1, Utrecht — moet ~77,07° (was fout: 44,1°); gebogen kopgevel,
  dus hier hoort het systeem 'controle nodig' te vlaggen i.p.v. stil te gokken.
"""

import json
import math
from pathlib import Path

import pytest

from energiemeneer_core import orientatie as o

_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "orientatie_panden.json").read_text()
)


def _laad(naam):
    d = _FIXTURES[naam]
    return {
        "vbo": tuple(d["vbo"]),
        "contour": [(x, y) for x, y in d["footprint"]],
        "straat_segmenten": [tuple(s) for s in d["straat_segs"]],
        "verwacht": d["verwacht"],
    }


# ─── Circulaire wiskunde ─────────────────────────────────────────────────────

def test_hoek_verschil_circulair():
    assert o.hoek_verschil(10, 350) == 20          # niet 340
    assert o.hoek_verschil(90, 270) == 180
    assert o.hoek_verschil(5, 5) == 0


def test_circulair_gemiddelde_rond_noord():
    # 350° en 10° → 0° (Noord), niet 180° (gewoon gemiddelde zou fout zijn).
    g = o.circulair_gemiddelde([350, 10])
    assert min(g, 360 - g) < 0.01


def test_circulaire_mediaan_negeert_uitschieter():
    # Drie panden rond 200°, één uitschieter op 30° → mediaan blijft bij de rij.
    m = o.circulaire_mediaan([198, 200, 202, 30])
    assert o.hoek_verschil(m, 200) <= 2


def test_hoek_naar_isso_grenzen():
    assert o.hoek_naar_isso(209.5) == "Zuidwest"
    assert o.hoek_naar_isso(0) == "Noord"
    assert o.hoek_naar_isso(359) == "Noord"
    assert o.hoek_naar_isso(90) == "Oost"


# ─── Losse schatters ─────────────────────────────────────────────────────────

def test_straat_loodrecht_simpel():
    # Straat loopt west-oost (langs de x-as) ten zuiden van het VBO; de voorgevel
    # kijkt dus naar het zuiden (180°).
    vbo = (0.0, 0.0)
    straat = [(-10.0, -10.0, 10.0, -10.0)]  # horizontaal, y=-10
    r = o.schat_straat_loodrecht(vbo, straat)
    assert r is not None
    assert o.hoek_verschil(r["hoek"], 180) < 1


def test_footprint_rand_zonder_straat_valt_terug():
    # Vierkant pand, VBO ten noorden van de bovenrand → zonder straat-hint kiest hij
    # de dichtstbijzijnde rand en kijkt naar buiten (noord, 0°).
    contour = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    vbo = (5.0, 20.0)
    r = o.schat_footprint_rand(contour, vbo, None)
    assert r is not None
    assert o.hoek_verschil(r["hoek"], 0) < 1


def test_buren_mediaan_minimaal_twee():
    assert o.schat_buren_mediaan([200]) is None          # te weinig
    r = o.schat_buren_mediaan([198, 202, 200])
    assert r is not None and o.hoek_verschil(r["hoek"], 200) <= 2


# ─── Samenvoegen / confidence ────────────────────────────────────────────────

def test_combineer_eens_geeft_hoog():
    r = o.combineer_schattingen([
        {"methode": "straat-loodrecht", "hoek": 209.5},
        {"methode": "footprint-rand", "hoek": 209.6},
    ])
    assert r["confidence"] == "hoog"
    assert r["controle_nodig"] is False
    assert o.hoek_verschil(r["hoek_graden"], 209.5) < 1


def test_combineer_oneens_flagt():
    r = o.combineer_schattingen([
        {"methode": "straat-loodrecht", "hoek": 65.1},
        {"methode": "footprint-rand", "hoek": 44.1},
    ])
    assert r["confidence"] == "laag"
    assert r["controle_nodig"] is True
    # Bij onenigheid wint het robuuste straat-anker.
    assert o.hoek_verschil(r["hoek_graden"], 65.1) < 1


def test_combineer_geen_schatting():
    r = o.combineer_schattingen([None, None])
    assert r["orientatie"] == "onbekend"
    assert r["controle_nodig"] is True


def test_combineer_buren_corrigeert_tussenwoning():
    # Footprint kiest een zijgevel (299°), straat ontbreekt, buren zeggen 209°.
    r = o.combineer_schattingen([
        {"methode": "footprint-rand", "hoek": 299.0},
        {"methode": "buren-mediaan", "hoek": 209.0},
    ], hoekpand=False)
    assert o.hoek_verschil(r["hoek_graden"], 209.0) < 1
    assert r["controle_nodig"] is True


def test_combineer_buren_corrigeert_hoekpand_niet():
    # Zelfde situatie maar hoekpand → buren NIET overnemen, wel flaggen.
    r = o.combineer_schattingen([
        {"methode": "footprint-rand", "hoek": 299.0},
        {"methode": "buren-mediaan", "hoek": 209.0},
    ], hoekpand=True)
    assert o.hoek_verschil(r["hoek_graden"], 299.0) < 1
    assert r["controle_nodig"] is True


# ─── Regressietests op de drie echte adressen (ingevroren geometrie) ─────────

@pytest.mark.parametrize("naam", [
    "Hendrick de Keyserstraat 68",
    "Hendrick de Keyserstraat 66",
])
def test_regressie_keyserstraat_zuidwest(naam):
    """Diepe rijtjeshuizen: de oude methode koos een zijgevel (~90° fout, 299,6°).
    Met het straat-anker moet het ~209° (Zuidwest) zijn, met hoge confidence."""
    f = _laad(naam)
    r = o.bepaal_orientatie("Hendrick de Keyserstraat", "68", "Utrecht",
                            vbo=f["vbo"], contour=f["contour"],
                            straat_segmenten=f["straat_segmenten"], buur_hoeken=[])
    assert o.hoek_verschil(r["hoek_graden"], f["verwacht"]) <= 5
    assert r["orientatie"] == "Zuidwest"
    assert r["confidence"] == "hoog"
    assert r["controle_nodig"] is False
    # De oude foute waarde (299,6° / Noordwest) mag niet meer terugkomen.
    assert o.hoek_verschil(r["hoek_graden"], 299.6) > 30


def test_regressie_stadhouderslaan_flagt():
    """Gebogen hoekpand: footprint (44°) en straat-loodrecht (65°) verschillen te
    veel. Het systeem hoort géén stille gok te geven maar 'controle nodig' te
    vlaggen — dan bevestigt Kevin handmatig (~77°)."""
    f = _laad("Stadhouderslaan 1")
    r = o.bepaal_orientatie("Stadhouderslaan", "1", "Utrecht",
                            vbo=f["vbo"], contour=f["contour"],
                            straat_segmenten=f["straat_segmenten"], buur_hoeken=[])
    assert r["confidence"] == "laag"
    assert r["controle_nodig"] is True
    # De oude foute waarde (44,1°) mag niet stilzwijgend als waarheid gelden:
    # het robuuste straat-anker (65°) is de getoonde kandidaat, en het dossier
    # wordt geflagd voor handmatige controle.
    assert o.hoek_verschil(r["hoek_graden"], 44.1) > 15
    alt_methodes = {a["methode"] for a in r["alternatieven"]}
    assert {"straat-loodrecht", "footprint-rand"} <= alt_methodes
