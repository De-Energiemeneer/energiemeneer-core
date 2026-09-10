import pytest

from energiemeneer_core import agenda_format


# Een complete klant + adres om mee te testen.
def _klant():
    return {
        "voornaam": "Jan",
        "achternaam": "Jansen",
        "email": "jan@example.nl",
        "telefoon": "0612345678",
        "opmerkingen": "Hond aanwezig",
    }


def _adres():
    return {
        "straatnaam": "Graskopstraat",
        "huisnummer": 8,
        "postcode": "2541 AB",
        "woonplaats": "'s-Gravenhage",
        "oppervlakte": 120,
        "bouwjaar": 1998,
        "label": "C",
    }


# ── Titel ────────────────────────────────────────────────────────────────────


def test_titel_oude_stijl_met_naam_opp_en_tijden():
    # 13:30Z = 15:30 Amsterdam (zomertijd), 15:00Z = 17:00.
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert r["onderwerp"] == (
        "Jan Jansen: Energielabel opname 120m² tussen 15:30 en 17:00 uur")


def test_titel_wintertijd_offset_plus_1():
    # 14:30Z = 15:30 Amsterdam (wintertijd, +1).
    r = agenda_format.opmaak_opname(
        "2026-01-15T14:30:00Z", "2026-01-15T16:00:00Z", _klant(), _adres())
    assert "tussen 15:30 en 17:00 uur" in r["onderwerp"]


def test_titel_zonder_oppervlakte_laat_m2_weg():
    adres = _adres()
    del adres["oppervlakte"]
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), adres)
    assert r["onderwerp"] == (
        "Jan Jansen: Energielabel opname tussen 15:30 en 17:00 uur")


def test_titel_zonder_naam_valt_terug_op_klant_onbekend():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", {}, _adres())
    assert r["onderwerp"].startswith("Klant onbekend: Energielabel opname")


# ── Locatie ────────────────────────────────────────────────────────────────────


def test_locatie_is_volledig_adres():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert r["locatie"] == "Graskopstraat 8, 2541 AB 's-Gravenhage"


def test_locatie_met_huisletter_en_toevoeging():
    adres = _adres()
    adres.update({"huisnummer": 8, "huisletter": "a", "toevoeging": "bis"})
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), adres)
    assert r["locatie"].startswith("Graskopstraat 8a-bis,")


# ── Body ────────────────────────────────────────────────────────────────────


def test_body_bevat_kerngegevens():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres(),
        woningtype="tussenwoning", prijs="315", label="C")
    body = r["body_html"]
    assert "Jan Jansen" in body
    assert "jan@example.nl" in body
    assert "0612345678" in body
    assert "Graskopstraat 8" in body
    # Woonplaats met apostrof komt HTML-veilig in de body.
    assert "2541 AB &#x27;s-Gravenhage" in body
    assert "Bouwjaar: 1998" in body
    assert "Oppervlakte: 120 m²" in body
    assert "Huidig label: <b>C</b>" in body
    assert "Woningtype: Tussenwoning" in body  # capitalize
    assert "Prijs: €315" in body
    assert "Hond aanwezig" in body


def test_makelaar_getoond_indien_ingevuld():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres(),
        makelaar="Makelaardij De Sleutel")
    assert "<b>Makelaar:</b>" in r["body_html"]
    assert "Makelaardij De Sleutel" in r["body_html"]


def test_makelaar_weggelaten_indien_leeg():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert "Makelaar:" not in r["body_html"]


def test_zakelijk_blok_alleen_bij_bedrijf():
    klant = _klant()
    klant["bedrijf"] = {"naam": "Acme BV", "kvk": "12345678", "btw": "NL0011B01"}
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", klant, _adres())
    body = r["body_html"]
    assert "— Zakelijk —" in body
    assert "Acme BV" in body
    assert "KvK: 12345678" in body
    assert "BTW: NL0011B01" in body


def test_geen_zakelijk_blok_zonder_bedrijf():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert "Zakelijk" not in r["body_html"]


def test_body_maakt_invoer_html_veilig():
    klant = _klant()
    klant["voornaam"] = "Jan & Co"
    klant["achternaam"] = "<script>"
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", klant, _adres())
    body = r["body_html"]
    assert "Jan &amp; Co" in body
    assert "&lt;script&gt;" in body
    assert "<script>" not in body
    # De titel is platte tekst (subject), die escapen we bewust niet.
    assert "Jan & Co <script>" in r["onderwerp"]


# ── Vaste waarden + eindtijd ────────────────────────────────────────────────────


def test_herinnering_is_60_minuten():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert r["herinner_minuten"] == 60


def test_bereken_eindtijd_voegt_90_minuten_toe():
    assert agenda_format.bereken_eindtijd("2026-06-01T13:30:00Z") == (
        "2026-06-01T15:00:00Z")


def test_returnt_velden_die_agenda_verwacht():
    r = agenda_format.opmaak_opname(
        "2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert set(r) == {"onderwerp", "body_html", "locatie", "herinner_minuten"}


# ── Fouten ────────────────────────────────────────────────────────────────────


def test_eist_start_en_eind():
    with pytest.raises(ValueError, match="start_iso en eind_iso"):
        agenda_format.opmaak_opname("", "2026-06-01T15:00:00Z", _klant(), _adres())


def test_onleesbare_tijd_geeft_duidelijke_fout():
    with pytest.raises(ValueError, match="Onleesbare tijd"):
        agenda_format.opmaak_opname("geen-tijd", "ook-niet", _klant(), _adres())


# ── B1 (10-9-2026): titel per product en markering in de body ────────────────


def test_zonder_product_blijft_titel_en_markering_energielabel():
    r = agenda_format.opmaak_opname("2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    assert r["onderwerp"] == "Jan Jansen: Energielabel opname 120m² tussen 15:30 en 17:00 uur"
    assert "[Energiemeneer-afspraak]" in r["body_html"]
    assert agenda_format.product_uit_body(r["body_html"]) == ""


def test_product_energielabel_is_byte_gelijk_aan_zonder_product():
    a = agenda_format.opmaak_opname("2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres())
    b = agenda_format.opmaak_opname("2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres(),
                                    product="Energielabel")
    assert a["onderwerp"] == b["onderwerp"] and a["locatie"] == b["locatie"]
    assert b["body_html"].replace("[Energiemeneer-afspraak: Energielabel]", "[Energiemeneer-afspraak]") == a["body_html"]


def test_vve_scan_titel_en_markering():
    r = agenda_format.opmaak_opname("2026-06-01T07:00:00Z", "2026-06-01T10:00:00Z", _klant(),
                                    {"straatnaam": "Sumatrastraat", "huisnummer": 200, "postcode": "2585CR",
                                     "woonplaats": "Den Haag"}, product="Energiescan VvE")
    assert r["onderwerp"] == "Jan Jansen: Energiescan VvE bezoek tussen 09:00 en 12:00 uur"
    assert "[Energiemeneer-afspraak: Energiescan VvE]" in r["body_html"]
    assert agenda_format.product_uit_body(r["body_html"]) == "Energiescan VvE"
    assert agenda_format.is_opname(r["onderwerp"], r["body_html"])
    assert not agenda_format.is_opname(r["onderwerp"])       # oude titelregel alleen kent dit woord niet


def test_is_opname_oude_titels_blijven_herkend():
    assert agenda_format.is_opname("Jan Jansen: Energielabel opname 120m² tussen 15:30 en 17:00 uur")
    assert agenda_format.is_opname("energielabel OPNAME", "")
    assert not agenda_format.is_opname("Tandarts", "<p>gewone afspraak</p>")
    assert agenda_format.is_opname("Tandarts", "<p>[energiemeneer-AFSPRAAK: Energielabel]</p>")


def test_onbekend_product_valt_terug_op_energielabel_woord():
    r = agenda_format.opmaak_opname("2026-06-01T13:30:00Z", "2026-06-01T15:00:00Z", _klant(), _adres(),
                                    product="Iets nieuws")
    assert "Energielabel opname" in r["onderwerp"]
    assert "[Energiemeneer-afspraak]" in r["body_html"]
