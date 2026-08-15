"""Microsoft-token ophalen, verversen en persistent bewaren (Module 5).

Bron: ``admin-portal/admin-portal/ms_graph.py`` — de schoonste auth-versie
(public client, geen client-secret in de requests, verse refresh-token
bewaren). Opnieuw geschreven volgens de core-conventies en uitgebreid met
een noodmelding via ntfy.sh.

Kerngedachte (lost K4 op — de terugkerende token-pijn):
  * Je logt één keer in via de Device Code Flow op het zakelijke account
    ``info@de-energiemeneer.nl``.
  * Microsoft geeft een langlevende **refresh-token**; die bewaren we in
    ``token_persist.json`` (plek bepaald door Module 1 ``storage``), zodat
    hij een herstart/verhuizing overleeft.
  * Het kortlevende **access-token** (~1 uur) houden we alleen in geheugen.
  * Bij elke verversing geeft Microsoft een verse refresh-token terug; die
    schrijven we direct terug. Zo verloopt de koppeling niet meer vanzelf.

De app is een **public client**: er gaat nooit een client-secret mee in de
token-requests. Er staan dan ook geen geheimen in deze code.

Noodmelding: kan de refresh-token écht niet meer ververst worden (Microsoft
zegt ``invalid_grant``), dan moet Kevin opnieuw inloggen. Omdat dan juist het
Microsoft-kanaal stuk is, sturen we de waarschuwing via een los kanaal
(ntfy.sh push). Max. één melding per 24 uur; het alarm reset zodra de login
weer slaagt. De melding bevat **geen klantgegevens**.

Zie BOUWPLAN.md, Module 5.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from energiemeneer_core import environment, storage

_log = logging.getLogger(__name__)

# Fake access-token voor dev/test (use_fake_clients): niet-leeg, geen netwerk.
_FAKE_ACCESS_TOKEN = "fake-access-token"

# ── Env-vars (geen geheimen — client-id/tenant-id staan open in Meesterbrein H9.2) ──
_ENV_CLIENT_ID = "MS_CLIENT_ID"
_ENV_TENANT_ID = "MS_TENANT_ID"
_ENV_REFRESH_TOKEN = "MS_REFRESH_TOKEN"  # optioneel eerste opstart-zetje
_ENV_NTFY_TOPIC = "ENERGIEMENEER_NTFY_TOPIC"
_ENV_NTFY_SERVER = "ENERGIEMENEER_NTFY_SERVER"

# Bekende, niet-geheime fallbacks (Meesterbrein H9.2).
_CLIENT_ID_FALLBACK = "75b57417-b3b0-4d9b-8162-79c36ded82e8"
_TENANT_ID_FALLBACK = "927d1e4a-d007-430e-9091-bc0c34214e3f"

# Scopes — basis exact zoals vastgelegd in BOUWPLAN/Meesterbrein H9.2.
# Mail.ReadWrite (16-8): nodig voor /me/messages/{id}/move — het archiveren van
# de OB-bewijskopie naar de mailmap 'Opdrachtbevestigingen'. Wordt bij het
# token-verversen met een VANGNET gevraagd: is de permissie (nog) niet
# toegekend in Entra, dan valt de verversing terug op de basis-scopes zodat
# de bestaande koppeling nooit breekt (zie _ververs_access_token).
_SCOPE_BASIS = (
    "Files.ReadWrite Tasks.ReadWrite Notes.ReadWrite "
    "Calendars.ReadWrite Mail.Send offline_access"
)
_SCOPE = _SCOPE_BASIS + " Mail.ReadWrite"

# Bestanden in de datamap (via Module 1 storage).
_TOKEN_BESTAND = "token_persist.json"
_ALARM_BESTAND = "graph_auth_alarm.json"

_NTFY_SERVER_STANDAARD = "https://ntfy.sh"
_ALARM_INTERVAL_SEC = 24 * 60 * 60  # max. één noodmelding per 24 uur
_VERLOOP_MARGE_SEC = 120  # ververs iets vóór het echt verloopt

# Tekst van de noodmelding — bewust zónder klantgegevens.
_ALARM_TITEL = "EnergieMeneer: Microsoft-inlog nodig"
_ALARM_BERICHT = (
    "Microsoft-koppeling vereist nieuwe inlog — "
    "draai claude in projectmap energiemeneer-core."
)

# In-memory cache voor het access-token (niet op schijf).
_access_cache: dict[str, Any] = {"token": None, "verloopt_op": 0.0}


# ── Endpoints ────────────────────────────────────────────────────────────────


def _tenant_id() -> str:
    import os

    return os.environ.get(_ENV_TENANT_ID, "").strip() or _TENANT_ID_FALLBACK


def _client_id() -> str:
    import os

    return os.environ.get(_ENV_CLIENT_ID, "").strip() or _CLIENT_ID_FALLBACK


def _token_endpoint() -> str:
    return f"https://login.microsoftonline.com/{_tenant_id()}/oauth2/v2.0/token"


def _devicecode_endpoint() -> str:
    return f"https://login.microsoftonline.com/{_tenant_id()}/oauth2/v2.0/devicecode"


# ── Publieke API ───────────────────────────────────────────────────────────────


def haal_graph_token() -> str:
    """Geef een geldig Microsoft access-token terug.

    Gebruikt het gecachte token zolang dat geldig is, ververst anders
    automatisch via de opgeslagen refresh-token.

    Raises:
        RuntimeError: er is nog geen refresh-token (eerst inloggen via
            :func:`start_device_login`), óf de refresh-token is definitief
            ongeldig (dan is ook een noodmelding verstuurd), óf Microsoft is
            tijdelijk onbereikbaar.
    """
    if environment.use_fake_clients():
        return _FAKE_ACCESS_TOKEN

    nu = time.time()
    token = _access_cache.get("token")
    if token and nu < _access_cache.get("verloopt_op", 0.0) - _VERLOOP_MARGE_SEC:
        return token

    refresh_token = _lees_refresh_token()
    if not refresh_token:
        raise RuntimeError(
            "Nog niet ingelogd bij Microsoft: er is geen refresh-token. "
            "Start de inlog met start_device_login()."
        )
    return _ververs_access_token(refresh_token)


def start_device_login() -> dict[str, Any]:
    """Start de Device Code Flow.

    Returns:
        Dict van Microsoft met o.a. ``user_code`` (de code die je inttypt),
        ``verification_uri`` (de pagina waar je inlogt), ``device_code``
        (nodig voor :func:`voltooi_device_login`), ``expires_in`` en
        ``interval``. Het veld ``message`` bevat de Nederlandstalige/Engelse
        instructie van Microsoft.

    Raises:
        RuntimeError: Microsoft gaf geen device code terug.
    """
    if environment.use_fake_clients():
        _log.info("[FAKE] device-login gestart — geen echte Microsoft-inlog nodig")
        return {
            "user_code": "FAKE-CODE",
            "verification_uri": "https://fake.local/devicelogin",
            "device_code": "fake-device-code",
            "expires_in": 900,
            "interval": 5,
            "message": "[FAKE] In dev/test is geen echte inlog nodig.",
        }

    try:
        r = requests.post(
            _devicecode_endpoint(),
            data={"client_id": _client_id(), "scope": _SCOPE},
            timeout=15,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Microsoft niet bereikbaar bij start inlog: {e}") from e

    if r.status_code != 200:
        raise RuntimeError(
            f"Inlog starten mislukt (HTTP {r.status_code}): {r.text[:300]}"
        )
    data = r.json()
    _log.info("Device Code Flow gestart — code %s", data.get("user_code"))
    return data


def voltooi_device_login(
    device_code: str,
    interval: int = 5,
    max_wachten_sec: int = 900,
) -> bool:
    """Wacht tot je via de browser bent ingelogd en bewaar dan de tokens.

    Args:
        device_code: het ``device_code`` uit :func:`start_device_login`.
        interval: aantal seconden tussen elke controle bij Microsoft.
        max_wachten_sec: maximale wachttijd (standaard 15 minuten).

    Returns:
        ``True`` zodra de login is gelukt; ``False`` bij time-out.

    Raises:
        RuntimeError: Microsoft meldde een echte fout (bijv. afgewezen).
    """
    if not device_code or not str(device_code).strip():
        raise ValueError("device_code is verplicht")

    if environment.use_fake_clients():
        _log.info("[FAKE] device-login voltooid — direct geslaagd, geen tokens bewaard")
        return True

    deadline = time.time() + max_wachten_sec
    while time.time() < deadline:
        time.sleep(interval)
        try:
            r = requests.post(
                _token_endpoint(),
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": _client_id(),
                    "device_code": device_code,
                },
                timeout=15,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Microsoft niet bereikbaar tijdens inlog: {e}") from e

        data = r.json()
        if r.status_code == 200:
            _verwerk_tokenrespons(data)
            _log.info("Inloggen bij Microsoft geslaagd")
            return True

        fout = data.get("error")
        if fout == "authorization_pending":
            continue  # nog niet ingelogd in de browser
        if fout == "slow_down":
            interval += 5
            continue
        raise RuntimeError(
            f"Inloggen mislukt: {fout} — {data.get('error_description', '')[:300]}"
        )

    _log.warning("Inloggen bij Microsoft afgebroken: time-out na %ss", max_wachten_sec)
    return False


def vergeet_access_token() -> None:
    """Vergeet het gecachte access-token, zodat de volgende aanvraag een
    vers token ophaalt.

    Gebruikt door ``graph_api`` als Microsoft midden in een aanroep een
    ``401`` geeft (token net verlopen): dan eerst vergeten, vers token halen
    en de aanroep één keer opnieuw proberen.
    """
    _access_cache["token"] = None
    _access_cache["verloopt_op"] = 0.0


# ── Verversen ──────────────────────────────────────────────────────────────────


def _ververs_access_token(refresh_token: str) -> str:
    """Haal een nieuw access-token op via de refresh-token.

    Bij ``invalid_grant`` (refresh-token definitief dood) wordt een
    noodmelding verstuurd en een ``RuntimeError`` geworpen. Bij een
    tijdelijke fout volgt alleen een ``RuntimeError`` (geen vals alarm).
    """
    def _post(scope: str) -> "requests.Response":
        return requests.post(
            _token_endpoint(),
            data={
                "grant_type": "refresh_token",
                "client_id": _client_id(),
                "refresh_token": refresh_token,
                "scope": scope,
            },
            timeout=15,
        )

    try:
        r = _post(_SCOPE)
        if r.status_code != 200:
            try:
                fout_vol = r.json().get("error", "")
            except ValueError:
                fout_vol = ""
            if fout_vol in ("invalid_grant", "interaction_required", "invalid_scope"):
                # Vangnet: de extra scope (Mail.ReadWrite) is mogelijk nog niet
                # toegekend in Entra. Probeer de basis-scopes — de koppeling
                # blijft dan gewoon werken; alleen het mail-verplaatsen wacht
                # op de consent. Faalt de basis óók, dan is de refresh-token
                # zelf het probleem en volgt het bestaande alarmpad.
                _log.warning(
                    "Token verversen met uitgebreide scope geweigerd (%s) — "
                    "terugval op basis-scopes; ken Mail.ReadWrite toe in Entra "
                    "voor het archiveren van mail", fout_vol)
                r = _post(_SCOPE_BASIS)
    except requests.RequestException as e:
        # Tijdelijk netwerkprobleem — geen alarm, gewoon later opnieuw.
        raise RuntimeError(f"Microsoft niet bereikbaar bij verversen: {e}") from e

    if r.status_code == 200:
        return _verwerk_tokenrespons(r.json())

    try:
        fout = r.json().get("error", "")
    except ValueError:
        fout = ""

    if fout in ("invalid_grant", "interaction_required"):
        # Refresh-token is definitief ongeldig: Kevin moet opnieuw inloggen.
        _log.error("Refresh-token afgewezen door Microsoft (%s)", fout)
        _waarschuw_opnieuw_inloggen()
        raise RuntimeError(
            "Microsoft-koppeling verlopen: opnieuw inloggen nodig "
            "(start_device_login). Er is een noodmelding verstuurd."
        )

    raise RuntimeError(
        f"Token verversen mislukt (HTTP {r.status_code}): {r.text[:300]}"
    )


def _verwerk_tokenrespons(data: dict[str, Any]) -> str:
    """Cache het access-token, bewaar een eventueel nieuwe refresh-token,
    en reset het noodmelding-alarm (login werkt weer)."""
    access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    _access_cache["token"] = access_token
    _access_cache["verloopt_op"] = time.time() + float(expires_in)

    nieuwe_refresh = data.get("refresh_token")
    if nieuwe_refresh:
        _bewaar_refresh_token(nieuwe_refresh)

    _reset_alarm()
    return access_token


# ── Refresh-token persistentie (via Module 1 storage) ────────────────────────


def _lees_refresh_token() -> str:
    """Lees de refresh-token: eerst uit ``token_persist.json``, anders uit
    de env-var ``MS_REFRESH_TOKEN`` (eenmalig opstart-zetje)."""
    data = storage.laad_json(_TOKEN_BESTAND, default={}) or {}
    token = (data.get("refresh_token") or "").strip()
    if token:
        return token

    import os

    return os.environ.get(_ENV_REFRESH_TOKEN, "").strip()


def _bewaar_refresh_token(refresh_token: str) -> None:
    if storage.bewaar_json(_TOKEN_BESTAND, {"refresh_token": refresh_token}):
        _log.info("Verse refresh-token opgeslagen in %s", _TOKEN_BESTAND)
    else:
        _log.error("Kon refresh-token niet opslaan in %s", _TOKEN_BESTAND)


# ── Noodmelding via ntfy.sh ──────────────────────────────────────────────────


def _waarschuw_opnieuw_inloggen() -> None:
    """Stuur één ntfy.sh-pushmelding dat opnieuw inloggen nodig is.

    Onafhankelijk van Microsoft. Max. één melding per 24 uur. Bevat geen
    klantgegevens. Best-effort: faalt de melding zelf, dan loggen we dat
    maar laten we de oorspronkelijke fout staan.
    """
    if not _alarm_mag_versturen():
        _log.info("Noodmelding onderdrukt (al binnen %sh verstuurd)", 24)
        return

    import os

    topic = os.environ.get(_ENV_NTFY_TOPIC, "").strip()
    if not topic:
        _log.warning(
            "Kan geen noodmelding sturen: env-var %s is niet gezet.",
            _ENV_NTFY_TOPIC,
        )
        return

    server = os.environ.get(_ENV_NTFY_SERVER, "").strip() or _NTFY_SERVER_STANDAARD
    try:
        r = requests.post(
            f"{server}/{topic}",
            data=_ALARM_BERICHT.encode("utf-8"),
            headers={
                "Title": _ALARM_TITEL,
                "Priority": "urgent",
                "Tags": "warning,key",
            },
            timeout=10,
        )
        if r.status_code < 300:
            _onthoud_alarm_verstuurd()
            _log.info("Noodmelding (ntfy) verstuurd")
        else:
            _log.error("Noodmelding mislukt: HTTP %s", r.status_code)
    except requests.RequestException as e:
        _log.error("Noodmelding kon niet verstuurd worden: %s", e)


def _alarm_mag_versturen() -> bool:
    data = storage.laad_json(_ALARM_BESTAND, default={}) or {}
    laatste = float(data.get("laatste_melding", 0) or 0)
    return (time.time() - laatste) >= _ALARM_INTERVAL_SEC


def _onthoud_alarm_verstuurd() -> None:
    storage.bewaar_json(_ALARM_BESTAND, {"laatste_melding": time.time()})


def _reset_alarm() -> None:
    """Wis het alarm-geheugen zodat een latere storing weer direct meldt."""
    data = storage.laad_json(_ALARM_BESTAND, default=None)
    if data and float(data.get("laatste_melding", 0) or 0) != 0:
        storage.bewaar_json(_ALARM_BESTAND, {"laatste_melding": 0})
