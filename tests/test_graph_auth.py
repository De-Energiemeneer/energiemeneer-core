from unittest.mock import MagicMock

import pytest
import requests

from energiemeneer_core import graph_auth, storage


@pytest.fixture(autouse=True)
def _verse_omgeving(tmp_path, monkeypatch):
    """Elke test krijgt een schone datamap + lege token-cache + ntfy-topic."""
    # Datamap-cache van storage resetten en naar tmp wijzen.
    storage._data_dir_cache = None
    monkeypatch.setenv(storage._ENV_FALLBACK, str(tmp_path))
    # Geen echte volume-paden laten meewegen.
    monkeypatch.setattr(storage, "_VOLUME_PADEN", ())
    # Access-token-cache leegmaken.
    graph_auth._access_cache["token"] = None
    graph_auth._access_cache["verloopt_op"] = 0.0
    # Onraadbare topic voor de noodmelding.
    monkeypatch.setenv(graph_auth._ENV_NTFY_TOPIC, "test-topic-xyz")
    monkeypatch.delenv(graph_auth._ENV_REFRESH_TOKEN, raising=False)
    # Niet echt slapen tijdens device-poll.
    monkeypatch.setattr(graph_auth.time, "sleep", lambda *_: None)
    yield


def _resp(status=200, json_data=None, text=""):
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.text = text
    return r


def _vang_post(monkeypatch, *responses):
    """Vervang requests.post; geeft de opeenvolgende responses terug."""
    calls: list[dict] = []
    seq = list(responses)

    def fake_post(url, data=None, headers=None, timeout=None, **kw):
        calls.append({"url": url, "data": data, "headers": headers})
        return seq.pop(0) if len(seq) > 1 else seq[0]

    monkeypatch.setattr(requests, "post", fake_post)
    return calls


# ── Verversen ────────────────────────────────────────────────────────────────


def test_gecached_token_geen_netwerk(monkeypatch):
    graph_auth._access_cache["token"] = "AT-cached"
    graph_auth._access_cache["verloopt_op"] = graph_auth.time.time() + 3600

    def boom(*a, **kw):
        raise AssertionError("er mag geen netwerkcall gebeuren")

    monkeypatch.setattr(requests, "post", boom)
    assert graph_auth.haal_graph_token() == "AT-cached"


def test_ververst_en_bewaart_nieuwe_refresh_token(monkeypatch):
    graph_auth._bewaar_refresh_token("RT-oud")
    calls = _vang_post(
        monkeypatch,
        _resp(json_data={"access_token": "AT-nieuw", "expires_in": 3600,
                         "refresh_token": "RT-nieuw"}),
    )
    token = graph_auth.haal_graph_token()
    assert token == "AT-nieuw"
    # Token-request gebruikt grant_type refresh_token en GEEN client_secret.
    assert calls[0]["data"]["grant_type"] == "refresh_token"
    assert "client_secret" not in calls[0]["data"]
    # Verse refresh-token is weggeschreven.
    bewaard = storage.laad_json(graph_auth._TOKEN_BESTAND)
    assert bewaard == {"refresh_token": "RT-nieuw"}


def test_geen_refresh_token_geeft_nette_fout(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("geen netwerkcall verwacht zonder refresh-token")

    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(RuntimeError, match="Nog niet ingelogd"):
        graph_auth.haal_graph_token()


def test_refresh_token_uit_env_als_bootstrap(monkeypatch):
    monkeypatch.setenv(graph_auth._ENV_REFRESH_TOKEN, "RT-env")
    calls = _vang_post(
        monkeypatch,
        _resp(json_data={"access_token": "AT", "expires_in": 3600}),
    )
    assert graph_auth.haal_graph_token() == "AT"
    assert calls[0]["data"]["refresh_token"] == "RT-env"


# ── Noodmelding ───────────────────────────────────────────────────────────────


def test_invalid_grant_stuurt_precies_een_noodmelding(monkeypatch):
    graph_auth._bewaar_refresh_token("RT-dood")
    calls = _vang_post(
        monkeypatch,
        _resp(status=400, json_data={"error": "invalid_grant"}),  # refresh (volle scope)
        _resp(status=400, json_data={"error": "invalid_grant"}),  # basis-scope-vangnet
        _resp(status=200),  # ntfy
    )
    with pytest.raises(RuntimeError, match="opnieuw inloggen"):
        graph_auth.haal_graph_token()

    ntfy_calls = [c for c in calls if "test-topic-xyz" in c["url"]]
    assert len(ntfy_calls) == 1
    # Melding bevat geen klantgegevens — alleen de vaste tekst.
    assert ntfy_calls[0]["data"] == graph_auth._ALARM_BERICHT.encode("utf-8")
    assert ntfy_calls[0]["url"].endswith("/test-topic-xyz")


def test_tweede_fout_binnen_24u_geen_tweede_melding(monkeypatch):
    graph_auth._bewaar_refresh_token("RT-dood")
    _vang_post(
        monkeypatch,
        _resp(status=400, json_data={"error": "invalid_grant"}),
        _resp(status=400, json_data={"error": "invalid_grant"}),
        _resp(status=200),
    )
    with pytest.raises(RuntimeError):
        graph_auth.haal_graph_token()

    # Tweede ronde: tel hoeveel ntfy-calls er nu nog bij komen.
    calls = _vang_post(
        monkeypatch,
        _resp(status=400, json_data={"error": "invalid_grant"}),
        _resp(status=400, json_data={"error": "invalid_grant"}),
        _resp(status=200),
    )
    with pytest.raises(RuntimeError):
        graph_auth.haal_graph_token()
    ntfy_calls = [c for c in calls if "test-topic-xyz" in c["url"]]
    assert ntfy_calls == []


def test_succesvolle_login_reset_alarm(monkeypatch):
    # Alarm staat "aan" (zojuist gemeld).
    graph_auth._onthoud_alarm_verstuurd()
    assert not graph_auth._alarm_mag_versturen()

    graph_auth._bewaar_refresh_token("RT")
    _vang_post(
        monkeypatch,
        _resp(json_data={"access_token": "AT", "expires_in": 3600,
                         "refresh_token": "RT2"}),
    )
    graph_auth.haal_graph_token()
    # Na geslaagde verversing mag een nieuwe storing weer direct melden.
    assert graph_auth._alarm_mag_versturen()


def test_zonder_topic_geen_melding_maar_wel_fout(monkeypatch):
    monkeypatch.delenv(graph_auth._ENV_NTFY_TOPIC, raising=False)
    graph_auth._bewaar_refresh_token("RT-dood")
    calls = _vang_post(
        monkeypatch,
        _resp(status=400, json_data={"error": "invalid_grant"}),
    )
    with pytest.raises(RuntimeError, match="opnieuw inloggen"):
        graph_auth.haal_graph_token()
    # Alleen de mislukte refresh-call, geen ntfy-call.
    assert all("ntfy" not in c["url"] and "/test-topic" not in c["url"] for c in calls)


# ── Tijdelijke fouten (géén alarm) ───────────────────────────────────────────


def test_netwerkfout_bij_verversen_geen_alarm(monkeypatch):
    graph_auth._bewaar_refresh_token("RT")

    def fake_post(*a, **kw):
        raise requests.ConnectionError("timeout")

    monkeypatch.setattr(requests, "post", fake_post)
    with pytest.raises(RuntimeError, match="niet bereikbaar"):
        graph_auth.haal_graph_token()
    # Geen alarm onthouden → een echte storing later mag nog melden.
    assert graph_auth._alarm_mag_versturen()


def test_tijdelijke_serverfout_geen_alarm(monkeypatch):
    graph_auth._bewaar_refresh_token("RT")
    _vang_post(monkeypatch, _resp(status=503, text="Service Unavailable"))
    with pytest.raises(RuntimeError, match="HTTP 503"):
        graph_auth.haal_graph_token()
    assert graph_auth._alarm_mag_versturen()


# ── Device Code Flow ─────────────────────────────────────────────────────────


def test_start_device_login_geeft_code(monkeypatch):
    _vang_post(
        monkeypatch,
        _resp(json_data={"user_code": "ABCD-1234",
                         "verification_uri": "https://microsoft.com/devicelogin",
                         "device_code": "DEV-CODE", "interval": 5}),
    )
    data = graph_auth.start_device_login()
    assert data["user_code"] == "ABCD-1234"


def test_voltooi_device_login_bewaart_token(monkeypatch):
    _vang_post(
        monkeypatch,
        _resp(status=400, json_data={"error": "authorization_pending"}),  # 1e poll: wachten
        _resp(json_data={"access_token": "AT", "expires_in": 3600,
                         "refresh_token": "RT-vers"}),         # 2e poll: klaar
    )
    assert graph_auth.voltooi_device_login("DEV-CODE", interval=0) is True
    assert storage.laad_json(graph_auth._TOKEN_BESTAND) == {"refresh_token": "RT-vers"}


def test_voltooi_device_login_echte_fout(monkeypatch):
    _vang_post(monkeypatch, _resp(status=400, json_data={"error": "access_denied"}))
    with pytest.raises(RuntimeError, match="access_denied"):
        graph_auth.voltooi_device_login("DEV-CODE", interval=0)


def test_scope_vangnet_valt_terug_op_basis(monkeypatch):
    """Mail.ReadWrite nog niet toegekend in Entra → de verversing met de
    uitgebreide scope wordt geweigerd, maar de basis-scope-retry slaagt:
    de koppeling blijft werken, zonder noodmelding."""
    graph_auth._bewaar_refresh_token("RT-goed")
    calls = _vang_post(
        monkeypatch,
        _resp(status=400, json_data={"error": "invalid_grant",
                                     "error_description": "AADSTS65001 consent"}),
        _resp(status=200, json_data={"access_token": "AT-basis", "expires_in": 3600}),
    )
    token = graph_auth.haal_graph_token()
    assert token == "AT-basis"
    # Eerste call vroeg de uitgebreide scope, het vangnet de basis-scopes.
    token_calls = [c for c in calls if "oauth2" in c["url"]]
    assert len(token_calls) == 2
    assert "Mail.ReadWrite" in token_calls[0]["data"]["scope"]
    assert "Mail.ReadWrite" not in token_calls[1]["data"]["scope"]
    # Geen noodmelding verstuurd.
    assert not [c for c in calls if "test-topic-xyz" in c["url"]]
