import pytest

from energiemeneer_core import email_format


def _afspraak():
    return {
        "token": "abc123token",
        "start": "2026-06-01T07:00:00Z",   # 09:00 Amsterdam (zomertijd)
        "end": "2026-06-01T08:30:00Z",     # 10:30 Amsterdam
        "klant": {
            "voornaam": "Jan",
            "achternaam": "Jansen",
            "email": "jan@example.nl",
            "telefoon": "0612345678",
        },
        "adres": {
            "straatnaam": "Graskopstraat",
            "huisnummer": 8,
            "postcode": "2541 AB",
            "woonplaats": "'s-Gravenhage",
            "oppervlakte": 120,
            "bouwjaar": 1998,
        },
        "woningtype": "tussenwoning",
        "prijs": "315",
        "label": "C",
    }


# ── _fmt_periode ──────────────────────────────────────────────────────────────


def test_periode_amsterdam_zomertijd():
    p = email_format._fmt_periode("2026-06-01T07:00:00Z", "2026-06-01T08:30:00Z")
    assert p["dag"] == "maandag"
    assert p["datum"] == "1 juni 2026"
    assert p["tijd"] == "09:00 – 10:30"
    assert p["duur"] == "90 minuten"


def test_periode_wintertijd_offset_plus_1():
    # 2026-01-05 08:00Z = 09:00 Amsterdam (wintertijd, +1)
    p = email_format._fmt_periode("2026-01-05T08:00:00Z", "2026-01-05T09:30:00Z")
    assert p["tijd"] == "09:00 – 10:30"
    assert p["dag"] == "maandag"


# ── bevestigingsmail ──────────────────────────────────────────────────────────


def test_bevestiging_onderwerp_en_body():
    subj, body = email_format.bevestigingsmail(
        _afspraak(), portal_url="https://portal.example.nl", intro_tekst="Bedankt voor je opdracht!")
    # 0.29.0 (Kevin 30-9): persoonlijke opmaak, u-vorm, geen gedachtestreepjes
    assert subj == "Afspraak bevestigd: maandag 1 juni 2026, van 09:00 tot 10:30 uur"
    assert "<p>Beste Jan Jansen,</p>" in body
    assert "Bedankt voor je opdracht!" in body          # intro komt uit de instelling
    assert "background:#EAF7EE" in body and "Maandag 1 juni 2026, van 09:00 tot 10:30 uur" in body
    assert "Adres: Graskopstraat 8, 2541 AB 's-Gravenhage" in body
    assert "https://portal.example.nl/a/abc123token" in body
    assert "—" not in subj + body and " – " not in body
    assert "Energielabel-opname" not in body and "je " not in body.replace("Bedankt voor je opdracht!", "")


def test_product_in_de_mail():
    a = _afspraak()
    a["product"] = "Maatwerkadvies particulier"
    _, body = email_format.bevestigingsmail(a, portal_url="https://p.nl", intro_tekst="x")
    assert "Product: Maatwerkadvies particulier" in body
    _, zonder = email_format.bevestigingsmail(_afspraak(), portal_url="https://p.nl", intro_tekst="x")
    assert "Product:" not in zonder


def test_bevestiging_opdrachtbevestiging_blok_ingevoegd():
    _, body = email_format.bevestigingsmail(
        _afspraak(), portal_url="https://p.nl", intro_tekst="x",
        opdrachtbevestiging_html="<div id='ob'>OB-blok</div>")
    assert "<div id='ob'>OB-blok</div>" in body


def test_portal_url_trailing_slash_genormaliseerd():
    _, body = email_format.bevestigingsmail(
        _afspraak(), portal_url="https://p.nl/", intro_tekst="x")
    assert "https://p.nl/a/abc123token" in body
    assert "https://p.nl//a/" not in body


# ── wijziging / annulering ────────────────────────────────────────────────────


def test_wijziging_onderwerp_en_kop():
    subj, body = email_format.wijzigingsmail(
        _afspraak(), portal_url="https://p.nl", intro_tekst="Gewijzigd.")
    assert subj == "Afspraak gewijzigd: maandag 1 juni 2026, van 09:00 tot 10:30 uur"
    assert "Nieuwe afspraak: maandag 1 juni 2026, van 09:00 tot 10:30 uur" in body
    assert "Gewijzigd." in body and "—" not in subj + body


def test_annulering_onderwerp_en_kop():
    subj, body = email_format.annuleringsmail(
        _afspraak(), portal_url="https://p.nl", intro_tekst="Geannuleerd.")
    assert subj == "Afspraak geannuleerd: maandag 1 juni 2026"
    assert "Geannuleerd." in body
    assert "line-through" in body  # doorgestreepte tijd
    assert "—" not in subj + body


# ── admin_notificatie ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("soort,vlag", [
    ("nieuw", "🟢 Nieuwe afspraak ingepland"),
    ("gewijzigd", "🟡 Afspraak gewijzigd door klant"),
    ("geannuleerd", "🔴 Afspraak geannuleerd door klant"),
])
def test_admin_notificatie_soorten(soort, vlag):
    subj, body = email_format.admin_notificatie(_afspraak(), soort)
    assert vlag in body
    assert subj.startswith(vlag + ": Jan Jansen")
    assert "jan@example.nl" in body and "0612345678" in body
    assert "abc123token" in body


def test_klant_naam_fallback():
    a = _afspraak()
    a["klant"] = {}
    subj, body = email_format.bevestigingsmail(a, portal_url="https://p.nl", intro_tekst="x")
    # zonder naam valt _klant_naam terug op "klant"
    assert "Beste klant," in body
