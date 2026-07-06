"""HTML-opmaak voor de klant- en admin-e-mails — het "merk" in de mailbox.

Bron: ``admin-portal/email_templates.py`` (de schoonste, in Outlook/Gmail/Apple
Mail geteste opmaak). Net als :mod:`energiemeneer_core.agenda_format` leeft deze
gebrande opmaak nu op één plek, zodat alle instroomkanalen dezelfde mails sturen.

Dit zijn **pure functies**: geen verzending, geen Graph, geen token. Je geeft een
afspraak-dict (+ portal-URL en intro-tekst), je krijgt ``(onderwerp, html_body)``
terug. Het versturen zelf doet de Graph-laag.

Levert vier mails:
  * :func:`bevestigingsmail`  — direct na inplannen (naar de klant)
  * :func:`wijzigingsmail`    — na wijziging door de klant
  * :func:`annuleringsmail`   — na annulering door de klant
  * :func:`admin_notificatie` — korte interne notificatie naar Kevin zelf

De afspraak-dict bevat ``start``/``end`` (UTC-ISO), ``token``, ``klant``
(``voornaam``/``achternaam``/``email``/``telefoon``), ``adres``, ``woningtype``,
``prijs`` en ``label`` — dezelfde vorm als de agenda- en opslag-laag gebruiken.

Zie BOUWPLAN.md, Module 7 (agenda_format/merk-laag).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

_log = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo

    _AMS: ZoneInfo | None = ZoneInfo("Europe/Amsterdam")
except Exception:  # pragma: no cover - tzdata hoort in de core te zitten
    _AMS = None

_DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
_MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni",
            "juli", "augustus", "september", "oktober", "november", "december"]


# ── Hulpjes ──────────────────────────────────────────────────────────────────


def _fmt_periode(start_iso: str, end_iso: str) -> dict[str, str]:
    """Lees begin/eind (UTC-ISO) en geef Amsterdamse dag/datum/tijd/duur terug."""
    def _parse(s: str) -> datetime:
        s2 = (s or "").replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if _AMS:
            return dt.astimezone(_AMS)
        # Ruwe fallback als zoneinfo ontbreekt (zou in de core niet moeten).
        return dt.replace(tzinfo=None) + timedelta(hours=2)

    s = _parse(start_iso)
    e = _parse(end_iso)
    duur = int((e - s).total_seconds() // 60)
    return {
        "dag": _DAGEN[s.weekday()],
        "datum": f"{s.day} {_MAANDEN[s.month - 1]} {s.year}",
        "tijd": f"{s.strftime('%H:%M')} – {e.strftime('%H:%M')}",
        "duur": f"{duur} minuten",
        "iso_kort": s.strftime("%Y-%m-%d %H:%M"),
    }


def _basis(*, titel: str, accent_kleur: str = "#0BBD37") -> tuple[str, str]:
    """Outer shell: header met logo, body-slot, footer. Geeft (head, footer)."""
    head = f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titel}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1a1a1a;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f5f5f5;padding:32px 0;">
  <tr><td align="center">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <!-- HEADER -->
      <tr><td style="background:#1a1a1a;padding:24px 32px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
          <tr>
            <td style="vertical-align:middle;">
              <span style="color:#fff;font-size:18px;font-weight:600;letter-spacing:0.2px;">De Energiemeneer</span>
            </td>
            <td align="right" style="vertical-align:middle;">
              <span style="color:{accent_kleur};font-size:12px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">Energielabel-opname</span>
            </td>
          </tr>
        </table>
      </td></tr>
"""
    # Slanke footer: de contactgegevens (e-mail, website, telefoon, KvK) staan nu in
    # de centraal geplakte handtekening vlak hierboven, dus hier alleen nog de
    # korte copyright-/legenda-regel — geen dubbele website-link meer.
    footer = f"""      <!-- FOOTER -->
      <tr><td style="padding:20px 32px 28px;background:#fafafa;border-top:1px solid #eeeeee;">
        <p style="margin:0;font-size:11px;color:#bbb;line-height:1.6;">© De Energiemeneer · Energielabels voor woningen</p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
    return head, footer


def _adres_str(adres: dict[str, Any] | None) -> str:
    a = adres or {}
    straat = (a.get("straatnaam") or "").strip()
    hn = str(a.get("huisnummer") or "").strip()
    hl = (a.get("huisletter") or "").strip()
    toev = (a.get("toevoeging") or "").strip()
    pc = (a.get("postcode") or "").strip()
    wp = (a.get("woonplaats") or "").strip()
    huisn = f"{hn}{hl}" + (f"-{toev}" if toev else "")
    return f"{straat} {huisn}, {pc} {wp}".strip(" ,")


def _klant_naam(klant: dict[str, Any] | None) -> str:
    k = klant or {}
    return f"{(k.get('voornaam') or '').strip()} {(k.get('achternaam') or '').strip()}".strip() or "klant"


def _detail_tabel(afspraak: dict[str, Any], periode: dict[str, str]) -> str:
    """Twee-koloms detail-tabel: label | waarde."""
    a = afspraak
    adres = _adres_str(a.get("adres"))
    rijen = [
        ("Datum", f"{periode['dag'].capitalize()} {periode['datum']}"),
        ("Tijd", f"{periode['tijd']} ({periode['duur']})"),
        ("Locatie", adres or "—"),
    ]
    woningtype = (a.get("woningtype") or "").strip()
    if woningtype:
        rijen.append(("Woningtype", woningtype.capitalize()))
    if a.get("adres", {}).get("oppervlakte"):
        rijen.append(("Oppervlakte", f"{a['adres']['oppervlakte']} m²"))
    if a.get("adres", {}).get("bouwjaar"):
        rijen.append(("Bouwjaar", str(a["adres"]["bouwjaar"])))
    if a.get("label"):
        rijen.append(("Huidig label", a["label"]))
    if a.get("prijs"):
        rijen.append(("Prijs", f"€ {a['prijs']}"))

    html = '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse:collapse;margin:0;">'
    for k, v in rijen:
        html += (
            "<tr>"
            f'<td style="padding:10px 0;border-bottom:1px solid #f0f0f0;font-size:13px;color:#888;width:130px;vertical-align:top;">{k}</td>'
            f'<td style="padding:10px 0;border-bottom:1px solid #f0f0f0;font-size:14px;color:#1a1a1a;font-weight:500;">{v}</td>'
            "</tr>"
        )
    html += "</table>"
    return html


def _knoppen(portal_url: str, token: str, primair: str = "wijzigen") -> str:
    """Knop "Afspraak bekijken" + de directe link. portal_url zonder trailing slash."""
    base = (portal_url or "").rstrip("/")
    link = f"{base}/a/{token}"
    btn_primair_kleur = "#0BBD37" if primair == "wijzigen" else "#1a1a1a"
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:24px 0 0;">
  <tr>
    <td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:0 6px;">
            <a href="{link}" style="display:inline-block;background:{btn_primair_kleur};color:#fff;font-size:14px;font-weight:600;text-decoration:none;padding:13px 28px;border-radius:30px;">
              Afspraak bekijken
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr><td align="center" style="padding-top:14px;">
    <a href="{link}" style="color:#888;font-size:12px;text-decoration:underline;">{link}</a>
  </td></tr>
</table>"""


# ── Hoofdfuncties ────────────────────────────────────────────────────────────


def bevestigingsmail(afspraak: dict[str, Any], *, portal_url: str, intro_tekst: str,
                     opdrachtbevestiging_html: str = "") -> tuple[str, str]:
    """E-mail die direct na inplannen naar de klant gaat."""
    periode = _fmt_periode(afspraak["start"], afspraak["end"])
    naam = _klant_naam(afspraak.get("klant"))
    head, foot = _basis(titel="Afspraak bevestigd")
    body = f"""      <!-- BODY -->
      <tr><td style="padding:36px 32px 8px;">
        <h1 style="margin:0 0 14px;font-size:24px;font-weight:600;color:#1a1a1a;letter-spacing:-0.2px;">
          Hallo {naam.split(' ')[0]}, je afspraak staat ingepland
        </h1>
        <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#555;">
          {intro_tekst}
        </p>

        <!-- Datum-callout -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
          <tr>
            <td style="background:#EAF7EE;border-left:4px solid #0BBD37;border-radius:6px;padding:18px 20px;">
              <div style="font-size:13px;color:#005a1a;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Wanneer</div>
              <div style="font-size:18px;font-weight:600;color:#1a1a1a;">{periode['dag'].capitalize()} {periode['datum']}</div>
              <div style="font-size:14px;color:#444;margin-top:2px;">{periode['tijd']} · {periode['duur']}</div>
            </td>
          </tr>
        </table>

        <!-- Details -->
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#888;margin-bottom:10px;">Afspraakgegevens</div>
        {_detail_tabel(afspraak, periode)}

        <!-- OPDRACHTBEVESTIGING_BLOK -->
        {opdrachtbevestiging_html or ''}

        <!-- Actieknoppen -->
        {_knoppen(portal_url, afspraak['token'], primair='wijzigen')}

        <p style="margin:32px 0 0;font-size:12px;color:#888;line-height:1.6;">
          Heb je vragen of wil je iets doorgeven over de woning?
          Antwoord gewoon op deze e-mail.
        </p>
      </td></tr>
"""
    return f"Afspraak bevestigd — {periode['dag']} {periode['datum']} {periode['tijd']}", head + body + foot


def wijzigingsmail(afspraak: dict[str, Any], *, portal_url: str, intro_tekst: str,
                   opdrachtbevestiging_html: str = "") -> tuple[str, str]:
    """E-mail na wijziging door klant."""
    periode = _fmt_periode(afspraak["start"], afspraak["end"])
    naam = _klant_naam(afspraak.get("klant"))
    head, foot = _basis(titel="Afspraak gewijzigd")
    body = f"""      <tr><td style="padding:36px 32px 8px;">
        <h1 style="margin:0 0 14px;font-size:24px;font-weight:600;color:#1a1a1a;">
          {naam.split(' ')[0]}, je nieuwe afspraak is bevestigd
        </h1>
        <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#555;">{intro_tekst}</p>

        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
          <tr><td style="background:#EAF7EE;border-left:4px solid #0BBD37;border-radius:6px;padding:18px 20px;">
              <div style="font-size:13px;color:#005a1a;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Nieuwe tijd</div>
              <div style="font-size:18px;font-weight:600;color:#1a1a1a;">{periode['dag'].capitalize()} {periode['datum']}</div>
              <div style="font-size:14px;color:#444;margin-top:2px;">{periode['tijd']} · {periode['duur']}</div>
          </td></tr>
        </table>

        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#888;margin-bottom:10px;">Afspraakgegevens</div>
        {_detail_tabel(afspraak, periode)}

        {opdrachtbevestiging_html or ''}

        {_knoppen(portal_url, afspraak['token'], primair='wijzigen')}
      </td></tr>
"""
    return f"Afspraak gewijzigd — {periode['dag']} {periode['datum']} {periode['tijd']}", head + body + foot


def annuleringsmail(afspraak: dict[str, Any], *, portal_url: str, intro_tekst: str) -> tuple[str, str]:
    """E-mail na annulering door klant."""
    naam = _klant_naam(afspraak.get("klant"))
    periode = _fmt_periode(afspraak["start"], afspraak["end"])
    head, foot = _basis(titel="Afspraak geannuleerd", accent_kleur="#888")
    body = f"""      <tr><td style="padding:36px 32px 8px;">
        <h1 style="margin:0 0 14px;font-size:24px;font-weight:600;color:#1a1a1a;">
          {naam.split(' ')[0]}, je afspraak is geannuleerd
        </h1>
        <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#555;">{intro_tekst}</p>

        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
          <tr><td style="background:#fafafa;border-left:4px solid #ccc;border-radius:6px;padding:18px 20px;">
              <div style="font-size:13px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Geannuleerd</div>
              <div style="font-size:16px;color:#666;text-decoration:line-through;">{periode['dag'].capitalize()} {periode['datum']} · {periode['tijd']}</div>
          </td></tr>
        </table>

        <p style="margin:24px 0 0;font-size:13px;color:#555;line-height:1.6;">
          Wil je een nieuwe afspraak inplannen? Antwoord op deze e-mail of bel ons.
        </p>
      </td></tr>
"""
    return f"Afspraak geannuleerd — {periode['dag']} {periode['datum']}", head + body + foot


def admin_notificatie(afspraak: dict[str, Any], soort: str = "nieuw") -> tuple[str, str]:
    """Korte interne notificatie naar Kevin zelf.

    soort: ``'nieuw'`` | ``'gewijzigd'`` | ``'geannuleerd'``.
    """
    periode = _fmt_periode(afspraak["start"], afspraak["end"])
    titels = {
        "nieuw": "🟢 Nieuwe afspraak ingepland",
        "gewijzigd": "🟡 Afspraak gewijzigd door klant",
        "geannuleerd": "🔴 Afspraak geannuleerd door klant",
    }
    titel = titels.get(soort, "Afspraak update")
    naam = _klant_naam(afspraak.get("klant"))
    adres = _adres_str(afspraak.get("adres"))
    email = (afspraak.get("klant") or {}).get("email", "")
    telef = (afspraak.get("klant") or {}).get("telefoon", "")

    body = f"""<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:14px;color:#222;line-height:1.6;max-width:560px;margin:24px auto;padding:0 16px;">
<h2 style="font-size:18px;margin:0 0 12px;">{titel}</h2>
<p style="margin:0 0 16px;color:#555;">{naam} · {email or '—'} · {telef or '—'}</p>
<table cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
  <tr><td style="color:#888;width:90px;">Wanneer</td><td><b>{periode['dag'].capitalize()} {periode['datum']}</b> · {periode['tijd']}</td></tr>
  <tr><td style="color:#888;">Locatie</td><td>{adres or '—'}</td></tr>
  <tr><td style="color:#888;">Token</td><td style="font-family:Menlo,monospace;font-size:11px;color:#666;">{afspraak.get('token','')}</td></tr>
</table>
</body></html>"""
    return f"{titel}: {naam} — {periode['datum']} {periode['tijd']}", body
