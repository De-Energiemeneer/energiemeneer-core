from unittest.mock import MagicMock

import pytest
import requests

from energiemeneer_core import graph_auth
from energiemeneer_core.graph_api import mail


@pytest.fixture(autouse=True)
def _altijd_geldig_token(monkeypatch):
    monkeypatch.setattr(graph_auth, "haal_graph_token", lambda: "AT-test")
    # Verzend-tests draaien met mail expliciet AAN; de "uit"-test zet zelf om.
    monkeypatch.setenv("MAIL_ENABLED", "1")
    yield


def _resp(status=202, json_data=None, text=""):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.text = text
    return r


def _vang_request(monkeypatch, response):
    calls: list[dict] = []

    def fake_request(method, url, headers=None, params=None, json=None,
                     data=None, timeout=None):
        calls.append({"method": method, "url": url, "json": json})
        return response

    monkeypatch.setattr(requests, "request", fake_request)
    return calls


def test_stuur_mail_enkel_adres(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    ok = mail.stuur_mail("klant@example.nl", "Hoi", "<b>test</b>")
    assert ok is True
    payload = calls[0]["json"]
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/me/sendMail")
    bericht = payload["message"]
    assert bericht["subject"] == "Hoi"
    assert bericht["body"] == {"contentType": "HTML", "content": "<b>test</b>"}
    assert bericht["toRecipients"] == [{"emailAddress": {"address": "klant@example.nl"}}]
    assert payload["saveToSentItems"] is True
    # Geen cc/bcc/replyTo als die niet zijn meegegeven.
    assert "ccRecipients" not in bericht
    assert "bccRecipients" not in bericht
    assert "replyTo" not in bericht


def test_stuur_mail_lijsten_en_cc_bcc_replyto(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    mail.stuur_mail(
        ["a@x.nl", "b@x.nl"], "Onderwerp", "<p>hoi</p>",
        cc="c@x.nl", bcc=["d@x.nl", "e@x.nl"], reply_to="info@de-energiemeneer.nl",
        opslaan_in_verzonden=False,
    )
    bericht = calls[0]["json"]["message"]
    assert [r["emailAddress"]["address"] for r in bericht["toRecipients"]] == ["a@x.nl", "b@x.nl"]
    assert [r["emailAddress"]["address"] for r in bericht["ccRecipients"]] == ["c@x.nl"]
    assert [r["emailAddress"]["address"] for r in bericht["bccRecipients"]] == ["d@x.nl", "e@x.nl"]
    assert bericht["replyTo"] == [{"emailAddress": {"address": "info@de-energiemeneer.nl"}}]
    assert calls[0]["json"]["saveToSentItems"] is False


def test_stuur_mail_zonder_bijlagen_geen_attachments_veld(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    mail.stuur_mail("a@x.nl", "x", "y")
    assert "attachments" not in calls[0]["json"]["message"]


def test_stuur_mail_inline_bijlage(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    logo = b"\x89PNG-nep-bytes"
    ok = mail.stuur_mail(
        "a@x.nl", "x", '<img src="cid:em-logo">',
        bijlagen=[{"naam": "logo.png", "content_type": "image/png",
                   "inhoud": logo, "inline": True, "content_id": "em-logo"}],
    )
    assert ok is True
    att = calls[0]["json"]["message"]["attachments"]
    assert len(att) == 1
    assert att[0]["@odata.type"] == "#microsoft.graph.fileAttachment"
    assert att[0]["name"] == "logo.png"
    assert att[0]["contentType"] == "image/png"
    assert att[0]["isInline"] is True
    assert att[0]["contentId"] == "em-logo"
    import base64 as _b
    assert _b.b64decode(att[0]["contentBytes"]) == logo


def test_stuur_mail_gewone_bijlage_niet_inline(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    mail.stuur_mail("a@x.nl", "x", "y",
                    bijlagen=[{"naam": "offerte.pdf", "content_type": "application/pdf",
                               "inhoud": b"%PDF-1.4"}])
    att = calls[0]["json"]["message"]["attachments"]
    assert att[0]["name"] == "offerte.pdf"
    assert "isInline" not in att[0] and "contentId" not in att[0]


def test_stuur_mail_slaat_kapotte_bijlage_over_en_verstuurt_toch(monkeypatch):
    # Een bijlage zonder inhoud/naam mag het versturen nooit blokkeren.
    calls = _vang_request(monkeypatch, _resp(status=202))
    ok = mail.stuur_mail(
        "a@x.nl", "x", "y",
        bijlagen=[{"naam": "", "inhoud": b"x"},               # geen naam
                  {"naam": "kapot.png", "inhoud": None},       # geen bytes
                  {"naam": "goed.png", "content_type": "image/png", "inhoud": b"ok"}],
    )
    assert ok is True
    att = calls[0]["json"]["message"]["attachments"]
    assert [a["name"] for a in att] == ["goed.png"]


def test_stuur_mail_inline_zonder_content_id_wordt_gewone_bijlage(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    mail.stuur_mail("a@x.nl", "x", "y",
                    bijlagen=[{"naam": "logo.png", "inhoud": b"x", "inline": True}])
    att = calls[0]["json"]["message"]["attachments"]
    assert att[0]["name"] == "logo.png"
    assert "isInline" not in att[0]


def test_stuur_mail_negeert_lege_adressen_in_lijst(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=202))
    mail.stuur_mail(["  ", "a@x.nl", ""], "x", "y")
    bericht = calls[0]["json"]["message"]
    assert [r["emailAddress"]["address"] for r in bericht["toRecipients"]] == ["a@x.nl"]


def test_stuur_mail_eist_ontvanger(monkeypatch):
    _vang_request(monkeypatch, _resp(status=202))
    with pytest.raises(ValueError, match="ontvanger"):
        mail.stuur_mail("", "Hoi", "<b>x</b>")
    with pytest.raises(ValueError, match="ontvanger"):
        mail.stuur_mail(["  ", ""], "Hoi", "<b>x</b>")


def test_stuur_mail_accepteert_200(monkeypatch):
    _vang_request(monkeypatch, _resp(status=200))
    assert mail.stuur_mail("a@x.nl", "x", "y") is True


def test_stuur_mail_overgeslagen_als_mail_uit(monkeypatch):
    # Mail uit via de policy-laag: niets versturen, False teruggeven.
    monkeypatch.setenv("MAIL_ENABLED", "0")
    calls = _vang_request(monkeypatch, _resp(status=202))
    assert mail.stuur_mail("a@x.nl", "x", "y") is False
    assert calls == []  # geen enkele HTTP-aanroep gedaan


def test_stuur_mail_fout(monkeypatch):
    _vang_request(monkeypatch, _resp(status=400, text="bad request"))
    with pytest.raises(RuntimeError, match="Mail versturen mislukt"):
        mail.stuur_mail("a@x.nl", "x", "y")


# ── Lezen (alleen-lezen) ─────────────────────────────────────────────────────
import base64 as _b64


def _vang_get_per_url(monkeypatch, url_naar_response):
    """Geef een verschillende response afhankelijk van het opgevraagde pad."""
    calls: list[dict] = []

    def fake_request(method, url, headers=None, params=None, json=None,
                     data=None, timeout=None):
        calls.append({"method": method, "url": url, "params": params})
        for fragment, resp in url_naar_response.items():
            if fragment in url:
                return resp
        return _resp(status=404, text="onbekend pad")

    monkeypatch.setattr(requests, "request", fake_request)
    return calls


def test_zoek_berichten_filtert_op_afzender_en_onderwerp(monkeypatch):
    waarde = {"value": [
        {"id": "1", "subject": "Afschrift energielabel 2521DV",
         "from": {"emailAddress": {"address": "noreply_eponline@rvo.nl"}},
         "receivedDateTime": "2026-06-01T10:00:00Z", "hasAttachments": True},
        {"id": "2", "subject": "Nieuwsbrief juni",
         "from": {"emailAddress": {"address": "noreply_eponline@rvo.nl"}},
         "receivedDateTime": "2026-06-02T10:00:00Z", "hasAttachments": True},
    ]}
    calls = _vang_get_per_url(monkeypatch, {"/me/messages": _resp(status=200, json_data=waarde)})
    res = mail.zoek_berichten(afzender="noreply_eponline@rvo.nl",
                              onderwerp_bevat="Afschrift energielabel",
                              alleen_met_bijlagen=True)
    # Onderwerp-filter laat alleen de afschrift-mail door.
    assert [b["id"] for b in res] == ["1"]
    assert res[0]["afzender"] == "noreply_eponline@rvo.nl"
    assert res[0]["heeft_bijlagen"] is True
    # Server-side filter bevat afzender + hasAttachments.
    flt = calls[0]["params"]["$filter"]
    assert "noreply_eponline@rvo.nl" in flt and "hasAttachments eq true" in flt


def test_zoek_berichten_sorteert_nieuwste_eerst(monkeypatch):
    waarde = {"value": [
        {"id": "oud", "subject": "Afschrift energielabel A",
         "from": {"emailAddress": {"address": "x@rvo.nl"}},
         "receivedDateTime": "2026-05-01T10:00:00Z", "hasAttachments": True},
        {"id": "nieuw", "subject": "Afschrift energielabel B",
         "from": {"emailAddress": {"address": "x@rvo.nl"}},
         "receivedDateTime": "2026-06-01T10:00:00Z", "hasAttachments": True},
    ]}
    _vang_get_per_url(monkeypatch, {"/me/messages": _resp(status=200, json_data=waarde)})
    res = mail.zoek_berichten(afzender="x@rvo.nl", onderwerp_bevat="Afschrift")
    assert [b["id"] for b in res] == ["nieuw", "oud"]


def test_zoek_berichten_fout(monkeypatch):
    _vang_get_per_url(monkeypatch, {"/me/messages": _resp(status=500, text="boem")})
    with pytest.raises(RuntimeError, match="Mails lezen mislukt"):
        mail.zoek_berichten(afzender="x@rvo.nl")


def test_zoek_berichten_map_naam_zoekt_in_die_map(monkeypatch):
    waarde = {"value": [
        {"id": "1", "subject": "Opdrachtbevestiging Acaciastraat 192",
         "from": {"emailAddress": {"address": "info@de-energiemeneer.nl"}},
         "toRecipients": [{"emailAddress": {"address": "Klant@Voorbeeld.nl"}}],
         "receivedDateTime": "2026-07-15T09:12:33Z",
         "sentDateTime": "2026-07-15T09:12:30Z", "hasAttachments": False},
    ]}
    calls = _vang_get_per_url(
        monkeypatch, {"/me/mailFolders/sentitems/messages": _resp(status=200, json_data=waarde)})
    res = mail.zoek_berichten(map_naam="sentitems", ontvanger="klant@voorbeeld.nl",
                              onderwerp_bevat="Opdrachtbevestiging")
    assert "/me/mailFolders/sentitems/messages" in calls[0]["url"]
    assert [b["id"] for b in res] == ["1"]
    assert res[0]["ontvangers"] == ["Klant@Voorbeeld.nl"]
    assert res[0]["verzonden"] == "2026-07-15T09:12:30Z"


def test_zoek_berichten_volgt_paginering(monkeypatch):
    """Een oudere mail op pagina 2 wordt gevonden zodra max > paginagrootte."""
    p1 = {"value": [{"id": f"nieuw{i}", "subject": "Iets anders",
                     "from": {"emailAddress": {"address": "info@x.nl"}},
                     "toRecipients": [{"emailAddress": {"address": "a@b.nl"}}],
                     "receivedDateTime": f"2026-08-01T10:{i:02d}:00Z",
                     "hasAttachments": False} for i in range(3)],
          "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/mailFolders/sentitems/messages?$skiptoken=xyz"}
    p2 = {"value": [{"id": "oud", "subject": "Opdrachtbevestiging Acaciastraat",
                     "from": {"emailAddress": {"address": "info@x.nl"}},
                     "toRecipients": [{"emailAddress": {"address": "klant@voorbeeld.nl"}}],
                     "receivedDateTime": "2026-06-13T13:05:00Z",
                     "sentDateTime": "2026-06-13T13:05:00Z", "hasAttachments": False}]}

    calls = []
    def fake_request(method, url, headers=None, params=None, json=None, data=None, timeout=None):
        calls.append(url)
        return _resp(status=200, json_data=(p2 if "skiptoken" in url else p1))
    monkeypatch.setattr(requests, "request", fake_request)

    res = mail.zoek_berichten(map_naam="sentitems", ontvanger="klant@voorbeeld.nl",
                              onderwerp_bevat="Opdrachtbevestiging", max=300)
    assert len(calls) == 2 and "skiptoken" in calls[1]
    assert [b["id"] for b in res] == ["oud"]


def test_zoek_berichten_search_query(monkeypatch):
    """$search: hele-map-zoekopdracht met ConsistencyLevel, zonder $filter/$orderby."""
    waarde = {"value": [{"id": "oud", "subject": "Opdrachtbevestiging Energielabel — Ananasstraat 109",
                         "from": {"emailAddress": {"address": "info@x.nl"}},
                         "toRecipients": [{"emailAddress": {"address": "ernst@haaksma.eu"}}],
                         "receivedDateTime": "2026-06-13T13:05:01Z",
                         "sentDateTime": "2026-06-13T13:05:00Z", "hasAttachments": False}]}
    calls = []
    def fake_request(method, url, headers=None, params=None, json=None, data=None, timeout=None):
        calls.append({"url": url, "params": params, "headers": headers})
        return _resp(status=200, json_data=waarde)
    monkeypatch.setattr(requests, "request", fake_request)

    res = mail.zoek_berichten(map_naam="sentitems", afzender="wordt@genegeerd.nl",
                              zoek_query='subject:Opdrachtbevestiging AND to:ernst@haaksma.eu',
                              ontvanger="ernst@haaksma.eu", onderwerp_bevat="Opdrachtbevestiging")
    p = calls[0]["params"]
    assert p["$search"] == '"subject:Opdrachtbevestiging AND to:ernst@haaksma.eu"'
    assert "$filter" not in p and "$orderby" not in p and p["$top"] == 25
    assert calls[0]["headers"].get("ConsistencyLevel") == "eventual"
    assert "/me/mailFolders/sentitems/messages" in calls[0]["url"]
    assert [b["id"] for b in res] == ["oud"]


def test_lijst_bijlagen_licht_zonder_inhoud(monkeypatch):
    waarde = {"value": [{"id": "a1", "name": "Offerte 200605.pdf",
                         "contentType": "application/pdf", "size": 12345},
                        {"id": "a2", "name": "Algemene Voorwaarden.pdf",
                         "contentType": "application/pdf", "size": 999}]}
    calls = _vang_get_per_url(monkeypatch, {"/attachments": _resp(status=200, json_data=waarde)})
    res = mail.lijst_bijlagen("msg-1")
    assert [b["naam"] for b in res] == ["Offerte 200605.pdf", "Algemene Voorwaarden.pdf"]
    # Licht: geen contentBytes in de $select.
    assert "contentBytes" not in calls[0]["params"]["$select"]
    with pytest.raises(ValueError):
        mail.lijst_bijlagen("")


def test_zoek_mailmap_id_topniveau_en_inbox(monkeypatch):
    top = {"value": [{"id": "map-1", "displayName": "Archief"}]}
    inbox = {"value": [{"id": "map-2", "displayName": "Opdrachtbevestigingen"}]}
    _vang_get_per_url(monkeypatch, {
        "/me/mailFolders/inbox/childFolders": _resp(status=200, json_data=inbox),
        "/me/mailFolders": _resp(status=200, json_data=top),
    })
    assert mail.zoek_mailmap_id("opdrachtbevestigingen") == "map-2"
    assert mail.zoek_mailmap_id("Archief") == "map-1"
    assert mail.zoek_mailmap_id("Bestaat Niet") == ""
    assert mail.zoek_mailmap_id("") == ""


def test_haal_bericht_geeft_body(monkeypatch):
    waarde = {"id": "1", "subject": "Opdrachtbevestiging X",
              "from": {"emailAddress": {"address": "info@x.nl"}},
              "toRecipients": [{"emailAddress": {"address": "klant@voorbeeld.nl"}}],
              "receivedDateTime": "2026-06-13T13:05:01Z",
              "sentDateTime": "2026-06-13T13:05:00Z", "hasAttachments": False,
              "body": {"contentType": "HTML", "content": "<p>Beste klant</p>"}}
    _vang_get_per_url(monkeypatch, {"/me/messages/1": _resp(status=200, json_data=waarde)})
    b = mail.haal_bericht("1")
    assert b["body_html"] == "<p>Beste klant</p>" and b["body_tekst"] == "Beste klant"
    assert b["verzonden"] == "2026-06-13T13:05:00Z"
    with pytest.raises(ValueError):
        mail.haal_bericht("")


def test_zoek_berichten_ontvanger_filtert_client_side(monkeypatch):
    waarde = {"value": [
        {"id": "goed", "subject": "Opdrachtbevestiging A",
         "from": {"emailAddress": {"address": "info@de-energiemeneer.nl"}},
         "toRecipients": [{"emailAddress": {"address": "klant@voorbeeld.nl"}}],
         "receivedDateTime": "2026-07-15T09:00:00Z", "hasAttachments": False},
        {"id": "ander", "subject": "Opdrachtbevestiging B",
         "from": {"emailAddress": {"address": "info@de-energiemeneer.nl"}},
         "toRecipients": [{"emailAddress": {"address": "iemand@anders.nl"}}],
         "receivedDateTime": "2026-07-16T09:00:00Z", "hasAttachments": False},
    ]}
    _vang_get_per_url(monkeypatch, {"/me/messages": _resp(status=200, json_data=waarde)})
    res = mail.zoek_berichten(ontvanger="klant@voorbeeld.nl")
    assert [b["id"] for b in res] == ["goed"]


def test_haal_bijlagen_decodeert_en_slaat_lege_over(monkeypatch):
    pdf = b"%PDF-1.4 testinhoud"
    waarde = {"value": [
        {"@odata.type": "#microsoft.graph.fileAttachment", "id": "a1",
         "name": "114060186_2521DV_297.pdf", "contentType": "application/pdf",
         "size": len(pdf), "contentBytes": _b64.b64encode(pdf).decode()},
        {"@odata.type": "#microsoft.graph.itemAttachment", "id": "a2",
         "name": "ingebed bericht", "contentType": "message/rfc822"},  # geen contentBytes
    ]}
    _vang_get_per_url(monkeypatch, {"/attachments": _resp(status=200, json_data=waarde)})
    res = mail.haal_bijlagen("msg-1")
    assert len(res) == 1
    assert res[0]["naam"] == "114060186_2521DV_297.pdf"
    assert res[0]["inhoud"] == pdf


def test_haal_bijlagen_eist_id(monkeypatch):
    with pytest.raises(ValueError, match="bericht_id"):
        mail.haal_bijlagen("")


def test_haal_bijlagen_stuurt_geen_select(monkeypatch):
    # Regressie (incident 06-08-2026): '$select=…,contentBytes' gaf altijd
    # HTTP 400 — 'contentBytes' bestaat alleen op het subtype fileAttachment,
    # niet op het attachment-basistype. De aanroep mag dus géén $select sturen.
    calls = _vang_get_per_url(monkeypatch, {"/attachments": _resp(status=200, json_data={"value": []})})
    mail.haal_bijlagen("msg-1")
    assert calls and not (calls[0]["params"] or {}).get("$select")


def test_zoek_berichten_met_body_geeft_html_en_platte_tekst(monkeypatch):
    waarde = {"value": [
        {"id": "1", "subject": "Uw beveiligingscode",
         "from": {"emailAddress": {"address": "info@energielabelportal.nl"}},
         "receivedDateTime": "2026-06-01T10:00:00Z", "hasAttachments": False,
         "body": {"contentType": "html",
                  "content": "<html><p>Uw   beveiligingscode is\n<b>123456</b>.</p></html>"}},
    ]}
    calls = _vang_get_per_url(monkeypatch, {"/me/messages": _resp(status=200, json_data=waarde)})
    res = mail.zoek_berichten(afzender="info@energielabelportal.nl", met_body=True)
    assert len(res) == 1
    assert "<b>123456</b>" in res[0]["body_html"]
    # Tags gestript, witruimte samengevouwen.
    assert res[0]["body_tekst"] == "Uw beveiligingscode is 123456 ."
    # body wordt alleen opgevraagd als erom gevraagd is.
    assert ",body" in calls[0]["params"]["$select"]


def test_zoek_berichten_zonder_body_vraagt_geen_body_op(monkeypatch):
    waarde = {"value": [
        {"id": "1", "subject": "X",
         "from": {"emailAddress": {"address": "a@b.nl"}},
         "receivedDateTime": "2026-06-01T10:00:00Z", "hasAttachments": False},
    ]}
    calls = _vang_get_per_url(monkeypatch, {"/me/messages": _resp(status=200, json_data=waarde)})
    res = mail.zoek_berichten(afzender="a@b.nl")
    assert "body" not in calls[0]["params"]["$select"]
    assert "body_html" not in res[0] and "body_tekst" not in res[0]


def test_verplaats_bericht_post_naar_move(monkeypatch):
    calls = _vang_request(monkeypatch, _resp(status=201, json_data={"id": "nieuw-id"}))
    nieuw = mail.verplaats_bericht("msg-1", "map-ob")
    assert nieuw == "nieuw-id"
    assert calls[0]["method"] == "POST"
    assert "/me/messages/msg-1/move" in calls[0]["url"]
    assert calls[0]["json"] == {"destinationId": "map-ob"}


def test_verplaats_bericht_fout_en_verplichte_velden(monkeypatch):
    _vang_request(monkeypatch, _resp(status=403, text="Access is denied"))
    with pytest.raises(RuntimeError, match="403"):
        mail.verplaats_bericht("msg-1", "map-ob")
    with pytest.raises(ValueError):
        mail.verplaats_bericht("", "map-ob")
    with pytest.raises(ValueError):
        mail.verplaats_bericht("msg-1", "")
