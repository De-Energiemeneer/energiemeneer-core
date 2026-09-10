import pytest

from energiemeneer_core import product


def test_catalogus_is_de_bekende_zeven_in_vaste_volgorde():
    assert product.namen() == (
        "Energielabel", "Herlabellen na advies", "Energielabel Advies",
        "Maatwerkadvies particulier", "Energiescan VvE", "Maatwerkadvies VvE",
        "Nog te bepalen")


def test_namen_en_slugs_zijn_uniek():
    namen = [p.naam for p in product.alle()]
    slugs = [p.slug for p in product.alle()]
    assert len(set(namen)) == len(namen)
    assert len(set(slugs)) == len(slugs)
    assert all(s == s.lower() and " " not in s for s in slugs)


def test_vind_en_profiel_tolerant_en_fail_safe():
    assert product.vind(" energielabel advies ").naam == "Energielabel Advies"
    assert product.vind("bestaat niet") is None
    assert product.vind(None) is None
    assert product.profiel("bestaat niet").naam == product.ONBEKEND
    assert product.profiel("").naam == product.ONBEKEND
    assert product.profiel("Energielabel").naam == "Energielabel"
    assert product.is_bekend("Maatwerkadvies VvE") and not product.is_bekend("x")


def test_van_slug():
    assert product.van_slug("maatwerkadvies").naam == "Maatwerkadvies particulier"
    assert product.van_slug("MAATWERKADVIES-VVE").naam == "Maatwerkadvies VvE"
    assert product.van_slug("onbekend") is None


def test_profielen_spiegelen_portalgedrag_9_9_2026():
    # Automaat-scope: de drie woningproducten (9-9) plus sinds B1 de VvE-scan,
    # die de OB alleen klaarzet (ob_automatisch=False). Offerteregels: woning
    # uit de m²-staffel, vve = vast tarief per complex.
    assert product.namen_met(automaat=True) == (
        "Energielabel", "Energielabel Advies", "Maatwerkadvies particulier", "Energiescan VvE")
    assert product.namen_met(automaat=True, ob_automatisch=True) == (
        "Energielabel", "Energielabel Advies", "Maatwerkadvies particulier")
    assert set(product.namen_met(offerteregels="woning")) == {
        "Energielabel", "Maatwerkadvies particulier", "Energielabel Advies"}
    assert product.namen_met(offerteregels="vve") == ("Energiescan VvE",)
    # Bijlage G: alleen de twee labelopnames.
    assert product.namen_met(bijlage_g=True) == ("Energielabel", "Energielabel Advies")
    # Factuurrobot: hele offerte → factuur; maatwerk = termijnen; onbekend = handmatig.
    assert product.namen_met(facturatie="robot") == (
        "Energielabel", "Herlabellen na advies", "Energielabel Advies", "Energiescan VvE")
    assert product.namen_met(facturatie="termijnen") == (
        "Maatwerkadvies particulier", "Maatwerkadvies VvE")
    # Dossiertype en mappenboom (vve_dossier.dossiertype, dossiermap_resolver.product_boom).
    assert product.namen_met(dossiertype="vve_maatwerk") == ("Maatwerkadvies VvE",)
    assert product.namen_met(dossiertype="vve_scan") == ("Energiescan VvE",)
    assert {p.naam: p.boom for p in product.alle()} == {
        "Energielabel": "labels", "Herlabellen na advies": "labels",
        "Energielabel Advies": "labels", "Maatwerkadvies particulier": "adviezen",
        "Energiescan VvE": "vve", "Maatwerkadvies VvE": "vve", "Nog te bepalen": "beide"}
    # Koepel: VvE nooit.
    assert product.namen_met(koepel=False) == ("Energiescan VvE", "Maatwerkadvies VvE")


def test_is_vve_via_profiel_met_substring_terugval():
    assert product.is_vve("Energiescan VvE") and product.is_vve("Maatwerkadvies VvE")
    assert not product.is_vve("Energielabel") and not product.is_vve(None)
    assert product.is_vve("VvE energieadvies (oud)")      # buiten de catalogus: oude regel
    assert not product.is_vve("Iets anders")


def test_namen_met_onbekend_veld_is_programmeerfout():
    with pytest.raises(AttributeError):
        product.namen_met(bestaat_niet=True)


def test_b1_vve_profielvelden_en_agenda_titel():
    """B1 (10-9-2026): nieuwe velden; woningproducten onveranderd (byte-gelijk)."""
    scan = product.profiel("Energiescan VvE")
    assert scan.automaat and not scan.ob_automatisch and not scan.woning_eisen
    assert scan.afspraak_vereist and scan.zelf_inplannen and scan.duur_minuten == 180
    assert scan.agenda_titel == "Energiescan VvE bezoek"
    assert product.profiel("Maatwerkadvies VvE").agenda_titel == "Maatwerkadvies VvE bezoek"
    for naam in ("Energielabel", "Herlabellen na advies", "Energielabel Advies",
                 "Maatwerkadvies particulier", "Nog te bepalen"):
        p = product.profiel(naam)
        assert p.ob_automatisch and p.woning_eisen and p.agenda_titel == "Energielabel opname", naam
    assert product.namen_met(woning_eisen=False) == ("Energiescan VvE", "Maatwerkadvies VvE")


def test_b2_3_agenda_categorie():
    """B2-3 (10-9-2026, beslissingen 21-23): labels / adviezen / vve; Energielabel
    Advies hoort bij de adviezen (beslissing 22)."""
    assert [k for k, _ in product.AGENDA_CATEGORIEEN] == ["labels", "adviezen", "vve"]
    assert product.agenda_categorie("Energielabel") == "labels"
    assert product.agenda_categorie("Herlabellen na advies") == "labels"
    assert product.agenda_categorie("Energielabel Advies") == "adviezen"
    assert product.agenda_categorie("Maatwerkadvies particulier") == "adviezen"
    assert product.agenda_categorie("Energiescan VvE") == "vve"
    assert product.agenda_categorie("Maatwerkadvies VvE") == "vve"
    assert product.agenda_categorie("bestaat niet") == "labels"
