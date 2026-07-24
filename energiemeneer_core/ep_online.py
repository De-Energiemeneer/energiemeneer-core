"""Energielabel-status via EP-Online v5.

Bron: ``admin-portal/server.py:204`` (``ep_online_lookup_raw``) —
opgesplitst in twee functies en omgezet naar ``requests`` met
geparseerde dict-return in plaats van rauwe ``(status, text)``-tuple.

Zie BOUWPLAN.md, Module 3.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from energiemeneer_core.bag import normaliseer_postcode

_log = logging.getLogger(__name__)

_EP_BASE = "https://public.ep-online.nl/api/v5"
_ENV_KEY_EP = "EP_ONLINE_KEY"


def zoek_op_vbo(vbo_id: str) -> dict[str, Any] | None:
    """Energielabel-status opvragen via VBO-ID.

    Returns:
        Dict met de EP-Online response (label, registratiedatum, …)
        of ``None`` als er voor dit VBO geen label geregistreerd is.

    Raises:
        ValueError: VBO-ID ontbreekt.
        RuntimeError: API-key ontbreekt of EP-Online geeft een fout.
    """
    if not vbo_id or not str(vbo_id).strip():
        raise ValueError("VBO-ID is verplicht")
    return _ep_get(f"/PandEnergielabel/AdresseerbaarObject/{vbo_id}")


def zoek_op_adres(
    postcode: str,
    huisnummer: int | str,
    huisletter: str | None = None,
    toevoeging: str | None = None,
) -> dict[str, Any] | None:
    """Energielabel-status opvragen via postcode + huisnummer.

    Postcode wordt eerst genormaliseerd (hoofdletters, geen spaties).
    ``huisletter`` en ``toevoeging`` zijn optioneel: alleen wanneer gevuld
    gaan ze mee als de v5-queryparameters ``huisletter`` respectievelijk
    ``huisnummertoevoeging`` — zonder deze parameters geeft EP-Online bij
    een sub-adres (bijv. 12A) het record van het basisnummer (12) terug.
    Leeg/None → parameter wordt niet meegestuurd (gedrag ongewijzigd).

    Returns:
        Dict met de EP-Online response of ``None`` als er voor dit adres
        geen label geregistreerd is.

    Raises:
        ValueError: postcode of huisnummer ontbreekt.
        RuntimeError: API-key ontbreekt of EP-Online geeft een fout.
    """
    pc = normaliseer_postcode(postcode)
    if not pc:
        raise ValueError("Postcode is verplicht")
    if huisnummer is None or str(huisnummer).strip() == "":
        raise ValueError("Huisnummer is verplicht")
    params = {"postcode": pc, "huisnummer": str(huisnummer)}
    if huisletter is not None and str(huisletter).strip():
        params["huisletter"] = str(huisletter).strip()
    if toevoeging is not None and str(toevoeging).strip():
        params["huisnummertoevoeging"] = str(toevoeging).strip()
    return _ep_get("/PandEnergielabel/Adres", params=params)


def _ep_get(path: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
    """Generieke EP-Online v5 call.

    Returnt parsed JSON bij 200, ``None`` bij 404 (geen label).
    Alle andere statuscodes worden vertaald naar ``RuntimeError``.
    """
    headers = {"Authorization": _api_key_ep()}
    url = _EP_BASE + path

    try:
        r = requests.get(url, headers=headers, params=params or {}, timeout=15)
    except requests.RequestException as e:
        raise RuntimeError(f"EP-Online niet bereikbaar ({path}): {e}") from e

    if r.status_code == 200:
        try:
            return r.json()
        except ValueError as e:
            raise RuntimeError(
                f"EP-Online gaf onverwachte response op {path}: {e}"
            ) from e
    if r.status_code == 404:
        return None
    if r.status_code == 401:
        raise RuntimeError("EP-Online 401: API-key ongeldig of verlopen")
    if r.status_code == 403:
        raise RuntimeError("EP-Online 403: geen rechten")
    try:
        detail = r.json()
    except ValueError:
        detail = r.text[:300]
    raise RuntimeError(f"EP-Online {r.status_code} op {path}: {detail}")


def _api_key_ep() -> str:
    key = os.environ.get(_ENV_KEY_EP, "").strip()
    if not key:
        raise RuntimeError(
            f"EP-Online API-key ontbreekt: zet env-var {_ENV_KEY_EP}"
        )
    return key
