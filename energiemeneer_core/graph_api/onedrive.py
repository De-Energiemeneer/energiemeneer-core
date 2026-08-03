"""OneDrive via Microsoft Graph — mappen aanmaken en bestanden uploaden.

Bron: ``aanmeldformulier_tool/ms_graph.py`` (``maak_onedrive_map`` +
``upload_bestand_onedrive``). Generiek gehouden: geen vaste mapnamen of
paden ingebakken — de aanroeper levert het volledige pad aan. (De vaste
EnergieMeneer-mapnaam-template "straat huisnr, woonplaats" hoort straks in
een aparte format-module, bijv. ``dossier_format``, niet hier.)

De slimme "naam al bezet → _1/_2"-logica voor de laatste map zit bewust
wél in de core: dat is generiek nuttig.

Upload kiest automatisch de juiste methode: kleine bestanden (≤ 4 MB) in
één keer, grotere via een upload-sessie in stukjes (veiligheidsnet voor
grote PDF's/foto's).

Zie BOUWPLAN.md, Module 6 (onderdeel 3).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from energiemeneer_core import environment
from energiemeneer_core.graph_api import _client

_log = logging.getLogger(__name__)

# Grens tussen simpele upload en upload-sessie (Microsoft-limiet ~4 MB).
_SIMPEL_MAX = 4 * 1024 * 1024
# Brokgrootte voor de upload-sessie — moet een veelvoud van 320 KiB zijn.
_CHUNK = 10 * 327680  # 3,2 MB


def maak_map(pad: str) -> dict[str, Any]:
    """Maak een (genest) mappad aan in OneDrive.

    Tussenliggende mappen worden aangemaakt als ze nog niet bestaan. De
    laatste map krijgt zo nodig een ``_1``/``_2``-achtervoegsel als de naam
    al bezet is.

    Args:
        pad: volledig pad, bijv. ``"1. Werkmap/Energielabels/Straat 8"``.

    Returns:
        Dict met ``pad`` (het uiteindelijk gebruikte pad) en ``mapnaam``
        (de uiteindelijke naam van de laatste map — kan afwijken door _1/_2).

    Raises:
        ValueError: leeg pad.
        RuntimeError: Graph geeft een fout.
    """
    onderdelen = [d for d in pad.strip("/").split("/") if d.strip()] if pad else []
    if not onderdelen:
        raise ValueError("pad is verplicht")

    basis_mappen, laatste_map = onderdelen[:-1], onderdelen[-1]

    huidig = ""
    for onderdeel in basis_mappen:
        parent = huidig or "root"
        huidig = f"{huidig}/{onderdeel}" if huidig else onderdeel
        if not _bestaat(huidig):
            _maak_submap(parent, onderdeel)

    # Unieke naam zoeken voor de laatste map.
    parent = huidig or "root"
    naam, teller = laatste_map, 1
    while _bestaat(_join(parent, naam)):
        naam = f"{laatste_map}_{teller}"
        teller += 1
    _maak_submap(parent, naam)

    uiteindelijk = _join(parent, naam)
    _log.info("OneDrive-map aangemaakt: %s", uiteindelijk)
    return {"pad": uiteindelijk, "mapnaam": naam}


def web_url(pad: str) -> str:
    """Geef de OneDrive-web-URL (browser-link) van een map of bestand.

    Args:
        pad: volledig pad t.o.v. de OneDrive-root.

    Returns:
        De ``webUrl`` van het item, of ``""`` als het niet gevonden wordt
        (bijv. nog niet aangemaakt) — bewust geen fout, zodat een dashboard-link
        gewoon kan ontbreken.
    """
    p = (pad or "").strip("/")
    if not p:
        return ""
    resp = _client.get(f"/me/drive/root:/{p}")
    if resp.status_code == 200:
        return resp.json().get("webUrl", "") or ""
    return ""


def lijst_bestanden(map_pad: str) -> list[dict[str, Any]]:
    """Som de inhoud van een OneDrive-map op (niet-recursief, alleen-lezen).

    Args:
        map_pad: volledig mappad t.o.v. de OneDrive-root.

    Returns:
        Lijst van dicts: ``naam``, ``grootte`` (bytes) en ``is_map`` (bool),
        voor elk item direct in de map. Volgt Graph-paginering, dus ook
        mappen met veel bestanden komen compleet terug.

    Raises:
        ValueError: leeg pad.
        RuntimeError: map niet gevonden of Graph geeft een fout.
    """
    p = (map_pad or "").strip("/")
    if not p:
        raise ValueError("map_pad is verplicht")

    items: list[dict[str, Any]] = []
    pad = f"/me/drive/root:/{p}:/children"
    params: dict[str, Any] | None = {"$select": "name,size,folder", "$top": 200}
    while pad:
        resp = _client.get(pad, params=params)
        if resp.status_code == 404:
            raise RuntimeError(f"OneDrive-map niet gevonden: {map_pad}")
        if resp.status_code != 200:
            raise RuntimeError(
                f"OneDrive-map lezen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        gegevens = resp.json()
        for item in gegevens.get("value", []):
            items.append({
                "naam": item.get("name", "") or "",
                "grootte": item.get("size", 0) or 0,
                "is_map": "folder" in item,
            })
        # Volgende pagina: Graph geeft een volledige URL; wij sturen alleen
        # het pad-deel door (de query met skiptoken zit daarin).
        volgende = gegevens.get("@odata.nextLink", "")
        pad = volgende.split("/v1.0", 1)[1] if "/v1.0" in volgende else ""
        params = None
    return items


def download_bestand(onedrive_pad: str, lokaal_pad: str, timeout: int = 15) -> str:
    """Download een OneDrive-bestand naar een lokaal pad.

    Args:
        onedrive_pad: volledig pad t.o.v. de OneDrive-root (incl. bestandsnaam).
        lokaal_pad: doelpad op de lokale schijf.
        timeout: HTTP-time-out in seconden (standaard 15 — gelijk aan de rest
            van de Graph-client). Grote bestanden (bijv. foto's in een
            dossiermap) kunnen langer nodig hebben; de aanroeper kan dan een
            ruimere time-out meegeven.

    Returns:
        Het lokale pad waar het bestand is weggeschreven.

    Raises:
        ValueError: bronpad ontbreekt.
        RuntimeError: bestand niet gevonden of Graph geeft een fout.
    """
    p = (onedrive_pad or "").strip("/")
    if not p:
        raise ValueError("onedrive_pad is verplicht")
    resp = _client.verzoek("GET", f"/me/drive/root:/{p}:/content", timeout=timeout)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"OneDrive-download mislukt ({resp.status_code}) voor {onedrive_pad}"
        )
    with open(lokaal_pad, "wb") as f:
        f.write(resp.content)
    _log.info("Bestand gedownload uit OneDrive: %s → %s", onedrive_pad, lokaal_pad)
    return lokaal_pad


def upload_bestand(lokaal_pad: str, onedrive_pad: str) -> dict[str, Any]:
    """Upload een lokaal bestand naar OneDrive.

    Kiest automatisch tussen simpele upload (≤ 4 MB) en een upload-sessie
    in stukjes (grotere bestanden).

    Args:
        lokaal_pad: pad naar het lokale bestand.
        onedrive_pad: doelpad in OneDrive (incl. bestandsnaam).

    Returns:
        Dict met ``pad`` en ``grootte`` (bytes).

    Raises:
        ValueError: doelpad ontbreekt.
        RuntimeError: bestand niet gevonden of Graph geeft een fout.
    """
    if not onedrive_pad or not onedrive_pad.strip():
        raise ValueError("onedrive_pad is verplicht")
    if not os.path.isfile(lokaal_pad):
        raise RuntimeError(f"Bestand niet gevonden: {lokaal_pad}")

    grootte = os.path.getsize(lokaal_pad)
    if grootte <= _SIMPEL_MAX:
        _upload_klein(lokaal_pad, onedrive_pad)
    else:
        _upload_groot(lokaal_pad, onedrive_pad, grootte)

    _log.info("Bestand geüpload naar OneDrive: %s (%d bytes)", onedrive_pad, grootte)
    return {"pad": onedrive_pad, "grootte": grootte}


def verplaats_item(pad: str, doel_map: str) -> dict[str, Any]:
    """Verplaats een bestand of map naar een andere OneDrive-map.

    De doelmap (inclusief tussenmappen) wordt aangemaakt als die nog niet
    bestaat. Bestaat er in de doelmap al een item met dezelfde naam, dan
    laat OneDrive het verplaatste item automatisch hernoemen (Graph-gedrag:
    er komt een volgnummer achter de naam).

    Args:
        pad: volledig pad van het te verplaatsen item t.o.v. de OneDrive-root.
        doel_map: volledig pad van de map waar het item heen moet.

    Returns:
        Dict met ``pad`` (het nieuwe volledige pad) en ``naam`` (de
        uiteindelijke naam — kan afwijken bij een naamsbotsing).

    Raises:
        ValueError: leeg bron- of doelpad.
        RuntimeError: item niet gevonden of Graph geeft een fout.
    """
    p = (pad or "").strip("/")
    d = (doel_map or "").strip("/")
    if not p:
        raise ValueError("pad is verplicht")
    if not d:
        raise ValueError("doel_map is verplicht")

    # Doelmap (met tussenmappen) garanderen — zonder de _1/_2-hernoemlogica
    # van maak_map: we willen verplaatsen naar precies déze map.
    huidig = ""
    for onderdeel in d.split("/"):
        if not onderdeel.strip():
            continue
        parent = huidig or "root"
        huidig = f"{huidig}/{onderdeel}" if huidig else onderdeel
        if not _bestaat(huidig):
            _maak_submap(parent, onderdeel)

    resp = _client.patch(
        f"/me/drive/root:/{p}",
        json={
            "parentReference": {"path": f"/drive/root:/{d}"},
            "@microsoft.graph.conflictBehavior": "rename",
        },
    )
    if resp.status_code == 404:
        raise RuntimeError(f"OneDrive-item niet gevonden: {pad}")
    if resp.status_code != 200:
        raise RuntimeError(
            f"OneDrive-item verplaatsen mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    naam = resp.json().get("name", "") or p.rsplit("/", 1)[-1]
    nieuw_pad = f"{d}/{naam}"
    _log.info("OneDrive-item verplaatst: %s → %s", pad, nieuw_pad)
    return {"pad": nieuw_pad, "naam": naam}


# ── Upload-varianten ───────────────────────────────────────────────────────────


def _upload_klein(lokaal_pad: str, onedrive_pad: str) -> None:
    with open(lokaal_pad, "rb") as f:
        inhoud = f.read()
    resp = _client.put_inhoud(f"/me/drive/root:/{onedrive_pad}:/content", inhoud)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Upload mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
        )


def _upload_groot(lokaal_pad: str, onedrive_pad: str, grootte: int) -> None:
    # De chunked upload gaat via een directe requests.put naar de sessie-URL —
    # buiten _client (en dus buiten de fake-swap) om. In fake-modus daarom hier
    # afvangen, zodat er geen echte netwerk-call naar een nep-URL ontstaat.
    if environment.use_fake_clients():
        _log.info(
            "[FAKE] grote upload %s (%d bytes) — overgeslagen (geen upload-sessie)",
            onedrive_pad, grootte,
        )
        return

    # Stap 1: vraag een upload-sessie aan.
    resp = _client.post(
        f"/me/drive/root:/{onedrive_pad}:/createUploadSession",
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Upload-sessie aanvragen mislukt (HTTP {resp.status_code}): "
            f"{resp.text[:300]}"
        )
    upload_url = resp.json().get("uploadUrl")
    if not upload_url:
        raise RuntimeError("Upload-sessie gaf geen uploadUrl terug")

    # Stap 2: stuur het bestand in stukjes. De uploadUrl is al voorzien van
    # toegang, dus hier géén Authorization-header.
    with open(lokaal_pad, "rb") as f:
        start = 0
        while start < grootte:
            brok = f.read(_CHUNK)
            eind = start + len(brok) - 1
            headers = {
                "Content-Length": str(len(brok)),
                "Content-Range": f"bytes {start}-{eind}/{grootte}",
            }
            try:
                r = requests.put(upload_url, data=brok, headers=headers, timeout=60)
            except requests.RequestException as e:
                raise RuntimeError(f"Upload-sessie niet bereikbaar: {e}") from e
            # 202 = brok ontvangen, 200/201 = klaar (laatste brok).
            if r.status_code not in (200, 201, 202):
                raise RuntimeError(
                    f"Upload-brok mislukt (HTTP {r.status_code}): {r.text[:300]}"
                )
            start = eind + 1


# ── Map-hulpjes ────────────────────────────────────────────────────────────────


def _bestaat(pad: str) -> bool:
    resp = _client.get(f"/me/drive/root:/{pad}")
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise RuntimeError(
        f"OneDrive-pad controleren mislukt (HTTP {resp.status_code}): {resp.text[:300]}"
    )


def _maak_submap(parent: str, naam: str) -> None:
    ep = (
        "/me/drive/root/children"
        if parent == "root"
        else f"/me/drive/root:/{parent}:/children"
    )
    resp = _client.post(
        ep,
        json={
            "name": naam,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        },
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Map aanmaken mislukt ({naam}, HTTP {resp.status_code}): {resp.text[:300]}"
        )


def _join(parent: str, naam: str) -> str:
    return naam if parent == "root" else f"{parent}/{naam}"
