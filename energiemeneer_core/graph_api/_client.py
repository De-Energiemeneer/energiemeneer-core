"""Intern loket voor Microsoft Graph-aanroepen.

Elke aanroep haalt zélf een geldig access-token op via Module 5
(``graph_auth.haal_graph_token``), zodat de onderdelen (agenda, mail, …)
nooit met tokens hoeven te werken.

Vangnet: geeft Microsoft een ``401`` (token net verlopen tijdens de
aanroep), dan vergeten we het gecachte token, halen een vers token en
proberen de aanroep precies één keer opnieuw.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from energiemeneer_core import environment, graph_auth
from energiemeneer_core.graph_api import _fake_client

_log = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _headers(token: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def verzoek(
    methode: str,
    pad: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
    data: bytes | None = None,
    headers_extra: dict[str, str] | None = None,
    timeout: int = 15,
) -> requests.Response:
    """Doe één Graph-aanroep met automatisch token + 401-herstel.

    Args:
        methode: ``GET`` / ``POST`` / ``PATCH`` / ``DELETE`` / ``PUT``.
        pad: pad ná de Graph-basis, bijv. ``/me/events``.
        json: JSON-body (voor de meeste aanroepen).
        data: rauwe bytes-body (voor bestand-uploads); geef dan zelf de
            juiste ``Content-Type`` mee via ``headers_extra``.

    Raises:
        RuntimeError: Microsoft Graph is niet bereikbaar.
    """
    if environment.use_fake_clients():
        return _fake_client.verzoek(
            methode, pad, params=params, json=json, data=data,
            headers_extra=headers_extra, timeout=timeout,
        )

    # Een volledige URL (bijv. een @odata.nextLink) gaat ongewijzigd door (0.23.1).
    url = pad if pad.startswith("http") else _GRAPH_BASE + pad

    def _doe(token: str) -> requests.Response:
        try:
            return requests.request(
                methode,
                url,
                headers=_headers(token, headers_extra),
                params=params,
                json=json,
                data=data,
                timeout=timeout,
            )
        except requests.RequestException as e:
            raise RuntimeError(
                f"Microsoft Graph niet bereikbaar ({methode} {pad}): {e}"
            ) from e

    resp = _doe(graph_auth.haal_graph_token())
    if resp.status_code == 401:
        _log.info("Graph gaf 401 op %s — vers token halen en opnieuw proberen", pad)
        graph_auth.vergeet_access_token()
        resp = _doe(graph_auth.haal_graph_token())
    return resp


def get(pad: str, *, params=None, headers_extra=None) -> requests.Response:
    return verzoek("GET", pad, params=params, headers_extra=headers_extra)


def post(pad: str, *, json=None, headers_extra=None) -> requests.Response:
    return verzoek("POST", pad, json=json, headers_extra=headers_extra)


def patch(pad: str, *, json=None, headers_extra=None) -> requests.Response:
    return verzoek("PATCH", pad, json=json, headers_extra=headers_extra)


def delete(pad: str, *, headers_extra=None) -> requests.Response:
    return verzoek("DELETE", pad, headers_extra=headers_extra)


def put_inhoud(
    pad: str, inhoud: bytes, content_type: str = "application/octet-stream"
) -> requests.Response:
    """PUT met rauwe bytes-body (voor het uploaden van bestandsinhoud)."""
    return verzoek("PUT", pad, data=inhoud, headers_extra={"Content-Type": content_type})
