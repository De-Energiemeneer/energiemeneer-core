"""E-mail via Microsoft Graph: versturen (``/me/sendMail``) en lezen
(``/me/messages``, alleen-lezen).

Bron: ``admin-portal/admin-portal/ms_graph.py`` (de generieke ``stuur_mail``)
en ``energielabel_upload_tool/backend/outlook_handler.py`` (mails + bijlagen
lezen). Bewust generiek: de aanroeper levert ontvanger(s)/filters, geen vaste
afzender of opmaak ingebakken.

De lees-functies (:func:`zoek_berichten`, :func:`haal_bijlagen`) zijn strikt
**alleen-lezen** — ze verwijderen, verplaatsen of markeren niets. Bedoeld voor
o.a. de upload-module (het EP-Online-afschrift ophalen). Enige uitzondering:
:func:`verplaats_bericht` verplaatst één bericht bewust naar een andere mailmap
(bewijskopie-archivering door de aanroeper, op mail-type).

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
    map_naam: str | None = None,
    ontvanger: str | None = None,
    zoek_query: str | None = None,
) -> list[dict]:
    """Lees berichten uit de mailbox van het ingelogde account (alleen-lezen).

    Filtert server-side op ``afzender`` (exacte match op het e-mailadres) en
    ``alleen_met_bijlagen``. ``onderwerp_bevat`` en ``ontvanger`` worden
    client-side gefilterd (Graph ``$filter`` ondersteunt geen ``contains`` op
    ``subject`` en geen ``any`` op ``toRecipients``).

    Args:
        afzender: alleen mails van dit exacte afzender-adres (hoofdletter-
            ongevoelig vergeleken; server-side gefilterd).
        onderwerp_bevat: alleen mails waarvan het onderwerp deze tekst bevat
            (hoofdletter-ongevoelig).
        alleen_met_bijlagen: alleen mails met minstens één bijlage.
        max: maximaal aantal RUWE berichten dat wordt bekeken. Boven de
            paginagrootte (100) volgt de functie de Graph-paginering
            (``@odata.nextLink``) tot dit aantal bereikt is — nodig om ook
            oudere mails te vinden vóórdat de client-side filters lopen.
        met_body: haal ook de berichttekst op. Voegt per bericht twee velden
            toe: ``body_html`` (de ruwe inhoud zoals Graph die geeft) en
            ``body_tekst`` (platte tekst, HTML-tags gestript) — bedoeld voor
            o.a. het uitlezen van een beveiligingscode uit een mail.
        map_naam: beperk het zoeken tot één mailmap — een well-known naam
            (bijv. ``"sentitems"`` voor Verzonden items) of een map-id.
            ``None`` = de hele mailbox (bestaand gedrag).
        ontvanger: alleen mails waarvan dit adres bij de ontvangers (Aan)
            staat (hoofdletter-ongevoelig; client-side) — bedoeld om een
            zelf-verstuurde mail in Verzonden items terug te vinden.
        zoek_query: KQL-zoekopdracht voor Graph ``$search`` (bijv.
            ``'subject:Opdrachtbevestiging AND to:klant@x.nl'``). Doorzoekt de
            HELE map via de zoekindex, ongeacht hoe diep de mail zit — dé
            manier om een oude mail te vinden zonder duizenden berichten te
            pagineren. Graph-eisen worden hier afgehandeld: header
            ``ConsistencyLevel: eventual``, geen ``$filter``/``$orderby`` in
            combinatie met ``$search`` (``afzender``/``alleen_met_bijlagen``
            worden dan genegeerd), paginagrootte ≤ 25. De resultaten komen op
            relevantie binnen; deze functie sorteert ze zelf op tijd en de
            client-side filters (``onderwerp_bevat``/``ontvanger``) blijven
            gewoon werken als verificatie.

    Returns:
        Lijst van dicts: ``id``, ``onderwerp``, ``afzender`` (e-mailadres),
        ``ontvangers`` (lijst Aan-adressen), ``ontvangen`` en ``verzonden``
        (ISO-tijd) en ``heeft_bijlagen`` (bool); met ``met_body`` ook
        ``body_html`` en ``body_tekst``. Nieuwste eerst.

    Raises:
        RuntimeError: Graph geeft een fout.
    """
    filters = []
    if afzender:
        veilig = afzender.replace("'", "''")
        filters.append(f"from/emailAddress/address eq '{veilig}'")
    if alleen_met_bijlagen:
        filters.append("hasAttachments eq true")

    select = "id,subject,from,toRecipients,receivedDateTime,sentDateTime,hasAttachments"
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

    # Paginering: Graph geeft per pagina maximaal ~100 berichten betrouwbaar
    # terug (bij $search maximaal 25); we volgen @odata.nextLink tot ``max``
    # RUWE berichten bekeken zijn. De filters (onderwerp/ontvanger) zijn
    # client-side en gaan dus over de volledige opgehaalde set — zonder
    # paginering zou een oudere mail buiten de eerste pagina onvindbaar zijn.
    maximaal = int(max)
    kop_extra = None
    if zoek_query:
        # $search laat geen $filter/$orderby toe en eist ConsistencyLevel.
        veilige_query = zoek_query.replace('"', " ").strip()
        params = {"$search": f'"{veilige_query}"',
                  "$top": min(maximaal, 25), "$select": select}
        kop_extra = {"ConsistencyLevel": "eventual"}
    else:
        params["$top"] = min(maximaal, 100)
    basis = f"/me/mailFolders/{map_naam}/messages" if map_naam else "/me/messages"
    ruwe: list[dict] = []
    pad = basis
    vraag: dict | None = params
    while pad and len(ruwe) < maximaal:
        resp = _client.get(pad, params=vraag, headers_extra=kop_extra)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Mails lezen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        gegevens = resp.json()
        pagina = gegevens.get("value", [])
        if not pagina:
            break   # lege pagina = klaar (sommige $search-antwoorden geven geen nextLink)
        ruwe.extend(pagina)
        volgende = gegevens.get("@odata.nextLink", "")
        pad = volgende.split("/v1.0", 1)[1] if "/v1.0" in volgende else ""
        vraag = None   # de nextLink bevat de query (skiptoken) al

    zoek = (onderwerp_bevat or "").lower()
    ontv_zoek = (ontvanger or "").strip().lower()
    berichten = []
    for m in ruwe[:maximaal]:
        onderwerp = m.get("subject", "") or ""
        if zoek and zoek not in onderwerp.lower():
            continue
        ontvangers = [((r.get("emailAddress") or {}).get("address") or "")
                      for r in (m.get("toRecipients") or [])]
        if ontv_zoek and ontv_zoek not in (a.lower() for a in ontvangers):
            continue
        berichten.append(_bericht_dict(m, met_body))
    berichten.sort(key=lambda b: b.get("ontvangen", ""), reverse=True)
    return berichten


def _bericht_dict(m: dict, met_body: bool) -> dict:
    """Eén Graph-bericht → het vaste resultaat-dict van deze module."""
    bericht = {
        "id": m.get("id", ""),
        "onderwerp": m.get("subject", "") or "",
        "afzender": (m.get("from", {}) or {}).get("emailAddress", {}).get("address", ""),
        "ontvangers": [((r.get("emailAddress") or {}).get("address") or "")
                       for r in (m.get("toRecipients") or [])],
        "ontvangen": m.get("receivedDateTime", ""),
        "verzonden": m.get("sentDateTime", "") or "",
        "heeft_bijlagen": bool(m.get("hasAttachments")),
    }
    if met_body:
        inhoud = (m.get("body", {}) or {}).get("content", "") or ""
        bericht["body_html"] = inhoud
        bericht["body_tekst"] = _naar_platte_tekst(inhoud)
    return bericht


def haal_bericht(bericht_id: str, met_body: bool = True) -> dict:
    """Haal één bericht op (alleen-lezen), met dezelfde velden als
    :func:`zoek_berichten` — inclusief de body. Bedoeld voor het patroon
    "licht zoeken (zonder bodies), daarna alleen de match volledig ophalen".

    Args:
        bericht_id: de Graph-``id`` van het bericht (uit :func:`zoek_berichten`).
        met_body: haal ook ``body_html``/``body_tekst`` op (standaard).

    Raises:
        ValueError: geen ``bericht_id``.
        RuntimeError: Graph geeft een fout.
    """
    if not bericht_id:
        raise ValueError("bericht_id is verplicht")
    select = "id,subject,from,toRecipients,receivedDateTime,sentDateTime,hasAttachments"
    if met_body:
        select += ",body"
    resp = _client.get(f"/me/messages/{bericht_id}", params={"$select": select})
    if resp.status_code != 200:
        raise RuntimeError(
            f"Bericht ophalen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    return _bericht_dict(resp.json(), met_body)


def _naar_platte_tekst(html: str) -> str:
    """Strip HTML-tags en vouw witruimte samen tot één regel platte tekst."""
    zonder_tags = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", zonder_tags).strip()


def zoek_mailmap_id(naam: str) -> str:
    """Zoek de map-id van een mailmap op weergavenaam (alleen-lezen).

    Kijkt hoofdletter-ongevoelig in de top-niveau-mappen én in de submappen
    van het Postvak IN — genoeg voor gebruikersmappen zoals
    "Opdrachtbevestigingen". De id is bruikbaar als ``map_naam`` in
    :func:`zoek_berichten`.

    Args:
        naam: de weergavenaam van de map.

    Returns:
        De Graph-``id`` van de map, of ``""`` als de map niet bestaat.

    Raises:
        RuntimeError: Graph geeft een fout.
    """
    doel = (naam or "").strip().lower()
    if not doel:
        return ""
    for pad in ("/me/mailFolders", "/me/mailFolders/inbox/childFolders"):
        resp = _client.get(pad, params={"$top": 200, "$select": "id,displayName"})
        if resp.status_code != 200:
            raise RuntimeError(
                f"Mailmappen lezen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        for m in resp.json().get("value", []):
            if (m.get("displayName") or "").strip().lower() == doel:
                return m.get("id", "") or ""
    return ""


def lijst_bijlagen(bericht_id: str) -> list[dict]:
    """Som de bijlagen van één bericht op ZONDER de inhoud te downloaden
    (alleen-lezen, licht). Bedoeld om een mail aan zijn bijlage-namen te
    herkennen (bijv. het vaste opdrachtbevestiging-pakket) zonder megabytes
    aan contentBytes op te halen — gebruik :func:`haal_bijlagen` als de
    inhoud zelf nodig is.

    Args:
        bericht_id: de Graph-``id`` van het bericht.

    Returns:
        Lijst van dicts: ``naam``, ``content_type`` en ``grootte`` (bytes).

    Raises:
        ValueError: geen ``bericht_id``.
        RuntimeError: Graph geeft een fout.
    """
    if not bericht_id:
        raise ValueError("bericht_id is verplicht")
    resp = _client.get(
        f"/me/messages/{bericht_id}/attachments",
        params={"$select": "id,name,contentType,size"},
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Bijlagen opsommen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    return [{"naam": a.get("name", "") or "",
             "content_type": a.get("contentType", "") or "",
             "grootte": a.get("size", 0) or 0}
            for a in resp.json().get("value", [])]


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

    # GEEN $select: 'contentBytes' bestaat alleen op het subtype
    # fileAttachment en Graph weigert het veld in een $select op het
    # attachment-basistype (HTTP 400 'Could not find a property named
    # contentBytes' — bewezen incident 06-08-2026, waardoor de offerte-
    # PDF-bewijsroute van de uploadtool nooit heeft gewerkt). Zonder
    # $select levert Graph bij bestand-bijlagen de inhoud gewoon mee.
    resp = _client.get(f"/me/messages/{bericht_id}/attachments")
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


def verplaats_bericht(bericht_id: str, doel_map: str) -> str:
    """Verplaats één bericht naar een andere mailmap.

    Dit is de ENIGE muterende functie aan de leeskant van deze module — de
    overige lees-functies blijven strikt alleen-lezen. Bedoeld voor het
    archiveren van een eigen (Bcc-)bewijskopie naar de juiste mailmap direct
    na het versturen, op basis van het mail-type dat de aanroeper zelf kent.

    Args:
        bericht_id: de Graph-``id`` van het bericht (uit :func:`zoek_berichten`).
        doel_map: de doelmap — een map-id (uit :func:`zoek_mailmap_id`) of een
            well-known naam zoals ``"archive"``.

    Returns:
        De nieuwe Graph-``id`` van het verplaatste bericht (verplaatsen geeft
        het bericht een andere id).

    Raises:
        ValueError: geen ``bericht_id`` of ``doel_map``.
        RuntimeError: Graph geeft een fout.
    """
    if not bericht_id:
        raise ValueError("bericht_id is verplicht")
    if not doel_map:
        raise ValueError("doel_map is verplicht")
    resp = _client.post(
        f"/me/messages/{bericht_id}/move", json={"destinationId": doel_map}
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Bericht verplaatsen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    nieuw = resp.json().get("id", "") or ""
    _log.info("Bericht %s verplaatst naar map %s", bericht_id, doel_map)
    return nieuw
