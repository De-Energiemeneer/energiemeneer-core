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
