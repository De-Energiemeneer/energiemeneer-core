"""E-mail via Microsoft Graph: versturen (``/me/sendMail``) en lezen
(``/me/messages``, alleen-lezen).

Bron: ``admin-portal/admin-portal/ms_graph.py`` (de generieke ``stuur_mail``)
en ``energielabel_upload_tool/backend/outlook_handler.py`` (mails + bijlagen
lezen). Bewust generiek: de aanroeper levert ontvanger(s)/filters, geen vaste
afzender of opmaak ingebakken.

De lees-functies (:func:`zoek_berichten`, :func:`haal_bijlagen`) zijn strikt
**alleen-lezen** — ze verwijderen, verplaatsen of markeren niets. Bedoeld voor
o.a. de upload-module (het EP-Online-afschrift ophalen).

Zie BOUWPLAN.md, Module 6 (onderdeel 2).
"""

from __future__ import annotations

import base64
import binascii
import logging
import re

from energiemeneer_core import environment
from energiemeneer_core.graph_api import _client

_log = logging.getLogger(__name__)

# Type voor "één adres of een lijst adressen".
Adressen = "str | list[str] | None"


def stuur_mail(
    naar: "str | list[str]",
    onderwerp: str,
    body_html: str,
    cc: "str | list[str] | None" = None,
    bcc: "str | list[str] | None" = None,
    reply_to: "str | list[str] | None" = None,
    opslaan_in_verzonden: bool = True,
    bijlagen: "list[dict] | None" = None,
) -> bool:
    """Verstuur een HTML-e-mail vanaf het ingelogde account.

    Args:
        naar: ontvanger(s) — één adres of een lijst.
        onderwerp: onderwerpregel.
        body_html: inhoud als HTML.
        cc, bcc, reply_to: optioneel, één adres of een lijst.
        opslaan_in_verzonden: bewaar de mail in "Verzonden items" (standaard).
        bijlagen: optionele lijst bijlage-dicts. Elke dict:

            * ``naam`` (str) — bestandsnaam;
            * ``content_type`` (str) — MIME-type, bijv. ``"image/png"``;
            * ``inhoud`` (bytes) — de ruwe bestand-bytes;
            * ``inline`` (bool, optioneel) — ``True`` voor een inline-afbeelding
              die via ``<img src="cid:...">`` in de body wordt getoond;
            * ``content_id`` (str, verplicht als ``inline``) — de ``cid`` die in
              de body naar deze afbeelding verwijst.

          Elke bijlage wordt een Graph ``fileAttachment``. Een bijlage zonder
          ``naam`` of ``inhoud`` wordt overgeslagen (luid gelogd) zodat één
          kapotte bijlage het versturen nooit blokkeert.

    Returns:
        ``True`` als Microsoft de mail heeft geaccepteerd. ``False`` als mail
        via de policy-laag uitstaat (``mail_enabled()`` is ``False``): dan wordt
        er niets verstuurd en alleen een logregel geschreven.

    Raises:
        ValueError: geen geldige ontvanger.
        RuntimeError: Graph geeft een fout.
    """
    ontvangers = _als_lijst(naar)
    if not ontvangers:
        raise ValueError("Minstens één ontvanger (naar) is verplicht")

    if not environment.mail_enabled():
        _log.info(
            "MAIL_ENABLED uit — mail aan %s overgeslagen (%s)",
            ", ".join(ontvangers), onderwerp,
        )
        return False

    bericht: dict = {
        "subject": onderwerp or "",
        "body": {"contentType": "HTML", "content": body_html or ""},
        "toRecipients": _adres_objecten(ontvangers),
    }
    cc_lijst = _als_lijst(cc)
    if cc_lijst:
        bericht["ccRecipients"] = _adres_objecten(cc_lijst)
    bcc_lijst = _als_lijst(bcc)
    if bcc_lijst:
        bericht["bccRecipients"] = _adres_objecten(bcc_lijst)
    reply_lijst = _als_lijst(reply_to)
    if reply_lijst:
        bericht["replyTo"] = _adres_objecten(reply_lijst)
    graph_bijlagen = _bijlage_objecten(bijlagen)
    if graph_bijlagen:
        bericht["attachments"] = graph_bijlagen

    payload = {"message": bericht, "saveToSentItems": opslaan_in_verzonden}
    resp = _client.post("/me/sendMail", json=payload)
    if resp.status_code not in (200, 202):
        raise RuntimeError(
            f"Mail versturen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    _log.info("Mail verstuurd aan %s — %s", ", ".join(ontvangers), onderwerp)
    return True


def _als_lijst(adressen: "str | list[str] | None") -> list[str]:
    """Maak van één adres of een lijst een schone lijst zonder lege waarden."""
    if not adressen:
        return []
    if isinstance(adressen, str):
        adressen = [adressen]
    return [a.strip() for a in adressen if a and a.strip()]


def _adres_objecten(adressen: list[str]) -> list[dict]:
    return [{"emailAddress": {"address": a}} for a in adressen]


def _bijlage_objecten(bijlagen: "list[dict] | None") -> list[dict]:
    """Zet de bijlage-dicts om naar Graph ``fileAttachment``-objecten.

    Een bijlage zonder ``naam`` of ``inhoud`` (of met niet-bytes-inhoud) wordt
    overgeslagen en luid gelogd — één kapotte bijlage mag het versturen nooit
    blokkeren. Inline-bijlagen krijgen ``isInline: true`` + ``contentId`` zodat
    ``<img src="cid:...">`` in de body werkt.
    """
    uit: list[dict] = []
    for b in bijlagen or []:
        if not isinstance(b, dict):
            _log.warning("Bijlage overgeslagen: geen dict (%s)", type(b).__name__)
            continue
        naam = (b.get("naam") or "").strip()
        inhoud = b.get("inhoud")
        if not naam or not isinstance(inhoud, (bytes, bytearray)):
            _log.warning("Bijlage '%s' overgeslagen: naam of inhoud (bytes) ontbreekt", naam or "?")
            continue
        att: dict = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": naam,
            "contentType": b.get("content_type") or "application/octet-stream",
            "contentBytes": base64.b64encode(bytes(inhoud)).decode("ascii"),
        }
        if b.get("inline"):
            content_id = (b.get("content_id") or "").strip()
            if not content_id:
                _log.warning("Inline-bijlage '%s' zonder content_id — als gewone bijlage meegestuurd", naam)
            else:
                att["isInline"] = True
                att["contentId"] = content_id
        uit.append(att)
    return uit


# ── Lezen (alleen-lezen) ─────────────────────────────────────────────────────
# Voor het ophalen van inkomende mails + bijlagen (bijv. het EP-Online-afschrift
# voor de upload-module). Strikt alleen-lezen: er wordt NIETS verwijderd,
# verplaatst of als gelezen gemarkeerd.

def zoek_berichten(
    afzender: str | None = None,
    onderwerp_bevat: str | None = None,
    alleen_met_bijlagen: bool = False,
    max: int = 50,
    met_body: bool = False,
) -> list[dict]:
    """Lees berichten uit de mailbox van het ingelogde account (alleen-lezen).

    Filtert server-side op ``afzender`` (exacte match op het e-mailadres) en
    ``alleen_met_bijlagen``. ``onderwerp_bevat`` wordt client-side gefilterd
    (Graph ``$filter`` ondersteunt geen ``contains`` op ``subject``).

    Args:
        afzender: alleen mails van dit exacte afzender-adres (hoofdletter-
            ongevoelig vergeleken; server-side gefilterd).
        onderwerp_bevat: alleen mails waarvan het onderwerp deze tekst bevat
            (hoofdletter-ongevoelig).
        alleen_met_bijlagen: alleen mails met minstens één bijlage.
        max: maximaal aantal mails om op te halen (Graph ``$top``).
        met_body: haal ook de berichttekst op. Voegt per bericht twee velden
            toe: ``body_html`` (de ruwe inhoud zoals Graph die geeft) en
            ``body_tekst`` (platte tekst, HTML-tags gestript) — bedoeld voor
            o.a. het uitlezen van een beveiligingscode uit een mail.

    Returns:
        Lijst van dicts: ``id``, ``onderwerp``, ``afzender`` (e-mailadres),
        ``ontvangen`` (ISO-tijd) en ``heeft_bijlagen`` (bool); met ``met_body``
        ook ``body_html`` en ``body_tekst``. Nieuwste eerst.

    Raises:
        RuntimeError: Graph geeft een fout.
    """
    filters = []
    if afzender:
        veilig = afzender.replace("'", "''")
        filters.append(f"from/emailAddress/address eq '{veilig}'")
    if alleen_met_bijlagen:
        filters.append("hasAttachments eq true")

    select = "id,subject,from,receivedDateTime,hasAttachments"
    if met_body:
        select += ",body"
    params: dict = {
        "$top": int(max),
        "$select": select,
    }
    if filters:
        # Bij een $filter op 'from' laat Graph geen $orderby op een ander veld
        # toe; we sorteren daarom zelf (client-side) op ontvangsttijd.
        params["$filter"] = " and ".join(filters)
    else:
        params["$orderby"] = "receivedDateTime desc"

    resp = _client.get("/me/messages", params=params)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Mails lezen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )

    zoek = (onderwerp_bevat or "").lower()
    berichten = []
    for m in resp.json().get("value", []):
        onderwerp = m.get("subject", "") or ""
        if zoek and zoek not in onderwerp.lower():
            continue
        bericht = {
            "id": m.get("id", ""),
            "onderwerp": onderwerp,
            "afzender": (m.get("from", {}) or {}).get("emailAddress", {}).get("address", ""),
            "ontvangen": m.get("receivedDateTime", ""),
            "heeft_bijlagen": bool(m.get("hasAttachments")),
        }
        if met_body:
            inhoud = (m.get("body", {}) or {}).get("content", "") or ""
            bericht["body_html"] = inhoud
            bericht["body_tekst"] = _naar_platte_tekst(inhoud)
        berichten.append(bericht)
    berichten.sort(key=lambda b: b.get("ontvangen", ""), reverse=True)
    return berichten


def _naar_platte_tekst(html: str) -> str:
    """Strip HTML-tags en vouw witruimte samen tot één regel platte tekst."""
    zonder_tags = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", zonder_tags).strip()


def haal_bijlagen(bericht_id: str) -> list[dict]:
    """Haal de bestandsbijlagen van één bericht op (alleen-lezen).

    Alleen echte bestand-bijlagen (``fileAttachment``) worden teruggegeven;
    inline-/item-bijlagen zonder inhoud worden overgeslagen.

    Args:
        bericht_id: de Graph-``id`` van het bericht (uit :func:`zoek_berichten`).

    Returns:
        Lijst van dicts: ``naam``, ``content_type``, ``grootte`` (bytes) en
        ``inhoud`` (de gedecodeerde bestand-bytes).

    Raises:
        ValueError: geen ``bericht_id``.
        RuntimeError: Graph geeft een fout.
    """
    if not bericht_id:
        raise ValueError("bericht_id is verplicht")

    resp = _client.get(
        f"/me/messages/{bericht_id}/attachments",
        params={"$select": "id,name,contentType,size,contentBytes"},
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Bijlagen ophalen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )

    bijlagen = []
    for a in resp.json().get("value", []):
        inhoud_b64 = a.get("contentBytes")
        if not inhoud_b64:
            # itemAttachment / referenceAttachment hebben geen contentBytes — overslaan.
            continue
        try:
            inhoud = base64.b64decode(inhoud_b64)
        except (binascii.Error, ValueError):
            continue
        bijlagen.append({
            "naam": a.get("name", "") or "",
            "content_type": a.get("contentType", "") or "",
            "grootte": a.get("size", 0) or len(inhoud),
            "inhoud": inhoud,
        })
    return bijlagen
