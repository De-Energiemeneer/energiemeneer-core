"""core.klant: factuuradres (bestaand) en het VvE-blok (B1, 10-9-2026)."""
from energiemeneer_core import klant


# ── Factuuradres: kern van het bestaande gedrag ──────────────────────────────

def test_factuuradres_uit_formulier_genest_en_plat():
    afw, adres = klant.uit_formulier({"factuuradres_afwijkend": True,
                                      "factuuradres": {"straat": "Laan", "huisnummer": "1",
                                                       "postcode": "1234 ab", "plaats": "Stad"}})
    assert afw is True and adres["postcode"] == "1234AB" and adres["toevoeging"] == ""
    afw, adres = klant.uit_formulier({"factuur_type": "ander", "factuur_straat": "Laan",
                                      "factuur_huisnummer": "2", "factuur_postcode": "1234AB",
                                      "factuur_plaats": "Stad"})
    assert afw is True and adres["huisnummer"] == "2"
    assert klant.uit_formulier({}) == (None, klant.schoon_factuuradres({}))


def test_factuuradres_van_valt_terug_op_woonadres():
    woon = {"straatnaam": "Weg", "huisnummer": "3", "postcode": "1111AA", "woonplaats": "Dorp"}
    r = klant.factuuradres_van({"factuuradres_afwijkend": False, "factuuradres": {}}, woon)
    assert r["bron"] == "woonadres" and r["straatnaam"] == "Weg"
    assert klant.adresregel(r) == "Weg 3, 1111AA Dorp"


# ── VvE-blok ─────────────────────────────────────────────────────────────────

def _vve():
    return {"vve_naam": " VvE Sumatrastraat 200-230 ", "kvk": "12.34 56 78",
            "contact_rol": "Bestuurslid", "beheerder": {"naam": "Beheer BV", "email": "info@beheer.nl"},
            "beheerder_rol": "via"}


def test_schoon_vve_normaliseert_rollen_kvk_en_adres():
    b = klant.schoon_vve(_vve())
    assert b["vve_naam"] == "VvE Sumatrastraat 200-230"
    assert b["kvk"] == "12345678"
    assert b["contact_rol"] == "bestuur" and b["beheerder_rol"] == "via"
    assert b["beheerder"] == {"naam": "Beheer BV", "email": "info@beheer.nl"}
    assert b["kvk_naam_officieel"] == "" and b["kvk_adres"] == klant.schoon_factuuradres({})
    assert set(b) == set(klant.VVE_VELDEN)


def test_schoon_kvk_alleen_acht_cijfers():
    assert klant.schoon_kvk("1234-5678") == "12345678"
    assert klant.schoon_kvk("1234567") == ""          # nooit een half nummer
    assert klant.schoon_kvk(None) == ""


def test_onbekende_rol_wordt_leeg_en_gemeld():
    b = klant.schoon_vve({"vve_naam": "VvE X", "contact_rol": "penningmeester?", "beheerder_rol": "misschien"})
    assert b["contact_rol"] == "" and b["beheerder_rol"] == ""
    mist = klant.vve_ontbrekende_velden(b)
    assert "rol van de contactpersoon (bestuur of beheerder)" in mist
    assert "rol van de beheerder (geen, via of opdrachtgever)" in mist


def test_vve_uit_formulier_genest_plat_en_afwezig():
    genest = klant.vve_uit_formulier({"vve": _vve()})
    assert genest and genest["kvk"] == "12345678"
    plat = klant.vve_uit_formulier({"vve_naam": "VvE Y", "vve_kvk": "87654321", "vve_contact_rol": "beheerder",
                                    "beheerder_naam": "Kantoor", "beheerder_email": "k@x.nl",
                                    "beheerder_rol": "opdrachtgever"})
    assert plat == klant.schoon_vve({"vve_naam": "VvE Y", "kvk": "87654321", "contact_rol": "beheerder",
                                     "beheerder": {"naam": "Kantoor", "email": "k@x.nl"},
                                     "beheerder_rol": "opdrachtgever"})
    assert klant.vve_uit_formulier({"voornaam": "Jan", "factuur_type": "ander"}) is None
    assert klant.vve_uit_formulier(None) is None


def test_vve_ontbrekende_velden_regels():
    assert klant.vve_ontbrekende_velden(_vve()) == []
    geen = {**_vve(), "beheerder_rol": "geen", "beheerder": {}}
    assert klant.vve_ontbrekende_velden(geen) == []          # zonder beheerder: geen naam/e-mail nodig
    zonder = {**_vve(), "beheerder": {"naam": "", "email": ""}}
    assert klant.vve_ontbrekende_velden(zonder) == ["naam van het beheerkantoor",
                                                     "e-mailadres van het beheerkantoor"]
    assert klant.vve_ontbrekende_velden({}) [0] == "naam van de VvE"
    # KvK is optioneel (niet elke VvE staat ingeschreven).
    assert klant.vve_ontbrekende_velden({**_vve(), "kvk": ""}) == []


def test_normaliseer_vve_en_beheerder_helpers():
    k = {"voornaam": "Jan", "vve": _vve()}
    assert klant.normaliseer_vve(k) is True
    assert klant.normaliseer_vve(k) is False              # idempotent
    assert klant.beheerder_in_cc(k) and not klant.beheerder_is_opdrachtgever(k)
    k["vve"]["beheerder_rol"] = "opdrachtgever"
    assert klant.beheerder_is_opdrachtgever(k) and not klant.beheerder_in_cc(k)
    part = {"voornaam": "Piet"}
    assert klant.normaliseer_vve(part) is False and "vve" not in part
    assert not klant.beheerder_in_cc(part)
