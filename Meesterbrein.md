# De EnergieMeneer — Meesterbrein (Platformarchitectuur)

**Van losse tools naar één online platform**

| | |
|---|---|
| **Versie** | 4.38 |
| **Laatst bijgewerkt** | 8 september 2026 |
| **Auteur** | Kevin Valkenhoff |
| **Bestandsnaam** | Meesterbrein.md *(vaste naam — verandert nooit)* |

_Centrale kennisbasis en kompas voor het bouwen van de Ultieme Tool, in samenwerking met Claude AI._

> **⚠️ INSTRUCTIE VOOR CLAUDE (chat én Claude Code) — versiebeheer, lees dit eerst:**
> Dit bestand heet **altijd** `Meesterbrein.md`. De bestandsnaam verandert **NOOIT** — niet hernoemen naar `Meesterbrein_v2.docx`, `Meesterbrein_v4_2.md` of welke genummerde variant dan ook. Het versienummer leeft **uitsluitend** in de tabel hierboven (regel "Versie"). Bij een wezenlijke wijziging: hoog dát nummer met één op (4.2 → 4.3 → …) en voeg een regel toe aan de versiehistorie (hoofdstuk 11). Lever het bestand altijd terug onder dezelfde naam `Meesterbrein.md`.
>
> Er bestaat precies één Meesterbrein, en die leeft op één plek: de **projectmap `energiemeneer-core`** (op GitHub). Het gekoppelde **Claude Project** leest het bestand **live vanuit GitHub** — na een push hoeft Kevin dus niets handmatig te uploaden of te vervangen. Eén bron van waarheid, geen genummerde kopieën laten rondslingeren.

# 0. Leeswijzer — hoe dit document werkt

Dit document is bewust anders opgezet dan de vorige versies (v1.0 t/m v3.1). Die beschreven “drie pijlers” die in de praktijk zijn uitgegroeid tot vijf losse tools. Versie 4.0 neemt het werkelijke einddoel als uitgangspunt: één online platform — een portal waar Kevin inlogt en al het werk doet, met één dashboard dat over alle functionaliteiten heen overzicht geeft (status, logs, foutmeldingen), gebouwd op één gedeeld fundament.

Het document scheidt nu vier soorten informatie, zodat het een stuurinstrument wordt in plaats van een verslag:

- **Architectuur (H3–H6)** — de stabiele laag: hoe het platform in elkaar zit (fundament + modules + portal + dashboard). Verandert zelden.

- **Modules (H7)** — elke tool als losse module met eigen status. Los bij te werken.

- **Contracten (H9)** — de bron van waarheid die de code moet volgen: prijzen, agenda-format, scopes, datamodel.

- **Roadmap (H10)** — wat eerst, en waarom. Verandert vaak.

> **Werkafspraak met Claude** Claude is de strategisch en technisch partner van Kevin Valkenhoff / De EnergieMeneer. Zoek altijd de meest optimale oplossing — ook buiten het kader van Kevin’s voorstel. Bij afwijking: benoem expliciet WAT en WAAROM. Groot denken is de norm, gericht op het hoofddoel. Communiceer in het Nederlands, informeel maar professioneel. Dit document is leidend; werk altijd binnen het Project en update dit document zodra de architectuur of een module wezenlijk verandert.

# 0a. Bouwstatus — waar staan we nu

> Deze sectie houdt de actuele voortgang bij, zodat elke nieuwe chat en elke Claude Code-sessie meteen weet waar het project staat. Werk dit bij zodra een module of fase verandert.

**Laatst bijgewerkt:** 7 juni 2026

**Fundament — `energiemeneer-core`** (Python-library, draait via Claude Code in de map `energiemeneer-core`, op GitHub/lokaal):

| Module | Status | Details |
| --- | --- | --- |
| 1. storage | ✅ Klaar | Atomic JSON-opslag, pad-detectie, lock. 9/9 tests groen. |
| 2. bag | ✅ Klaar | Adres- + vrij zoeken (BAG + PDOK). 12/12 tests groen. |
| 3. ep_online | ✅ Klaar | Label-status via VBO of adres. 10/10 tests groen. |
| 4. prijs | ✅ Klaar | Prijsmatrix incl. spoed + maatwerk. 31/31 tests groen. Uitgebreid in **v0.2.0** met publieke drempelwaarden + helpers (`krijg_matrix`, `is_nieuwbouw`, `NIEUWBOUW_JAAR_VANAF`, `MAATWERK_BOVEN_M2`) zodat consumers geen eigen prijs-feiten meer hoeven te kennen. |
| 5. graph_auth | ✅ Klaar | Microsoft-token: public client, refresh-rotatie in token_persist.json, ntfy-noodmelding bij verlopen koppeling. 13/13 tests groen. |
| 6. graph_api | ✅ Klaar | Alle onderdelen af: ✅ agenda, ✅ mail, ✅ onedrive, ✅ todo, ✅ onenote. Uitgebreid in **v0.5.0** met `onedrive.web_url(pad)` (deelbare OneDrive-link), **v0.6.0** met **mail-lezen** (`mail.zoek_berichten`/`haal_bijlagen`, alleen-lezen), **v0.7.0** met `agenda.haal_agenda_op` incl. locatie+id, en **v0.8.0** met **To Do-lezen** (`todo.lees_lijsten`/`lees_taken`, alleen-lezen; onbekende lijst → leeg, geen aanmaak) voor de dashboard-sectie "Dossiers in behandeling". 198/198 tests groen. |
| 7. agenda_format | ✅ Klaar | Vaste Outlook-opmaak losgekoppeld van de agenda-laag. 17/17 tests groen. In **v0.7.0** geeft `agenda.haal_agenda_op` ook `locatie` + `id` terug, zodat de dossiervoorbereiding opname-afspraken (met het adres in de locatie) live uit de agenda kan lezen. |
| 8. events | ✅ Klaar | Centrale append-only logging (fundament dashboard). schrijf_event + lees_events met filters; strikte resultaat-/niveau-waarden; JSONL bovenop storage. 16/16 tests groen. **Hele core nu af: 159/159 tests.** |

**Omgeving:** Claude Code geïnstalleerd op Windows via WSL/Ubuntu. Oude tools staan als leesbron in `OneDrive/1. Werkmap/Claude/Automatiseringstools` (alleen lezen). Geen API-keys in de nieuwe code — alles via env-vars. Oude hardcoded keys (BAG ×2, EP ×1) moeten nog geroteerd worden (zie H8.3).

**Bevinding voor toekomst:** Railway-account 'keviniom' heeft via de GitHub-app Repository access = All repositories ingesteld. Railway kan dus zonder extra configuratie bij alle huidige én toekomstige repos in het Keviniom-account, inclusief private repos zoals energiemeneer-core. Geldt ook voor de geïnstalleerde Anthropic Claude GitHub-app.

**Fundament — fase F1:** ✅ **volledig af** — core compleet (Modules 1–8, 159/159 tests groen).

**Fase 2 (F2) — admin-portal volledig op de core:** ✅ **afgerond** (6 juni 2026). Alle gedeelde logica van de admin-portal komt nu uit `energiemeneer-core`: postcode, prijs, bag, ep_online, agenda-opmaak, bestand-IO, mailopmaak én de Microsoft Graph-koppeling.
- ✅ **F2.0** — `energiemeneer-core` installeerbaar als Python-package via pip.
- ✅ **F2.2 Stap 1a (plumbing)** — core als dependency + postcode-test, géén gedragsverandering. Bewezen op Railway PR-environment `admin-portal-pr-1`.
- ✅ **F2.2 Stap 1b (postcode-vervanging)** — `normaliseer_postcode` in `server.py` vervangen door `core.bag.normaliseer_postcode`, lokale duplicaat verwijderd. **Gemerged naar main; productie draait nu op de core voor postcode-normalisatie.**
- ✅ **Bonus-fixes meegenomen in dezelfde PR (#1):** domein-typo overal gefixt naar `de-energiemeneer.nl` (met streepje — de admin-notificatie bouncede op het niet-bestaande adres zonder streepje) en tijdformaat-fix (agenda-titel toont nu "13:00 en 14:30 uur" met dubbele punten i.p.v. "1300").
- ✅ **F2.2 Stap 2 (prijs)** — `bereken_prijs` in `server.py` vervangen door een dunne adapter rond `core.prijs.bereken_prijs` + `core.prijs.is_nieuwbouw` (tegen tag **v0.2.0**); output-vorm `{prijs, maatwerk, label}` en de quirk (onbekend type → Maatwerk) bewust behouden. Lokale `PRIJSMATRIX`-duplicaat én het ongebruikte, admin-gated `/api/prijzen`-endpoint verwijderd; `/api/prijs` (live berekening) blijft. Spoedtoeslag bewust ongemoeid (gedragsneutraal). Pariteitstest verbeterd: importeert nu de **échte** `server.bereken_prijs` en vergelijkt met de bevroren oude logica (`_OUD_*`), groen in een kale omgeving zonder secrets (334/334). **Gemerged via PR #4; productie rekent prijzen nu via de core.**
- ✅ **F2.2 Stap 3 (bag)** — `bag_lookup` in `server.py` vervangen door een dunne adapter rond `core.bag.zoek_adres` (tegen tag **v0.2.0**); het `/api/adres`-contract exact behouden (`{ok: true, ...velden...}` / `{error: ...}`). Lokale `bag_lookup`-duplicaat én de hardcoded BAG-fallback-sleutel verwijderd — `core.bag` eist `OVERHEID_API_KEY` strikt via env-var (geen fallback meer), die staat nu op Railway (preview + productie). Volledige-pariteitstest `tests/test_adres_pariteit.py`: bevroren verbatim-kopie van de oude `bag_lookup` vs de nieuwe adapter, beide gevoed met identieke gemockte BAG-JSON; groen incl. kale omgeving (5/5), geen regressie (prijs 334/334, postcode 6/6). Huisletter-bug (frictie #7) bewust niet aangeraakt — gedragsneutraal. **Gemerged via PR #5; productie zoekt adressen nu via de core.**
- ✅ **F2.2 Stap 4 (ep_online)** — de EP-Online-labelstatus achter `/api/ep` vervangen door een dunne adapter (`ep_online_lookup`) rond `core.ep_online.zoek_op_vbo` / `zoek_op_adres` (tegen tag **v0.2.0**). Het oude pad deed rauwe `(status, text)`-passthrough; de core geeft geparseerd / `None` / raise. Contract naar de frontend exact behouden: succes → zelfde JSON-array, geen label (EP 404) → `[]`, input ontbreekt → 400, EP-fout/ontbrekende key → HTTP 200 met foutenvelop (frontend toont "Geen label"). Bewuste keuze: de frontend (`fetchLabel`) leunt alleen op de body, niet op de HTTP-status, dus die blijft 200 behalve bij ontbrekende input. Hardcoded EP-fallback-sleutel verwijderd — `core.ep_online` eist `EP_ONLINE_KEY` strikt via env-var (geen fallback meer), staat nu op Railway (preview + productie). Contract-pariteitstest `tests/test_ep_pariteit.py` (oud urllib-pad vs nieuw core-pad, identieke gemockte EP-responses): 6/6 groen incl. kale omgeving, geen regressie (adres 5/5, prijs 334/334, postcode 6/6). Triviale opschoning: ongebruikte `urllib`-imports verwijderd. **Gemerged via PR #6; productie haalt labelstatus nu via de core.**
- ✅ **F2.2 Stap 5 (Outlook-opmaak)** — de lokale opmaak van de opname-afspraak (titel + HTML-body + locatie; `_bouw_event_body` + titelopbouw in `ms_graph.py`) vervangen door `core.agenda_format.opmaak_opname` (tegen tag **v0.2.0**). **Alleen de opmaak** — de `ms_graph`-/Graph-aanroepen zelf blijven nog lokaal (latere stap); de start/eind-tijd voor het event blijft lokaal (UTC → Amsterdam). Eerst vergeleken, geen blinde swap: pariteitstest `tests/test_agenda_opmaak_pariteit.py` legt een bevroren verbatim-kopie van de oude opmaak naast de core op 8 representatieve gevallen — titel, tijd (UTC→Amsterdam incl. zomertijd), `m²`-uit-titel bij onbekende oppervlakte, locatie en body identiek. **Twee bewust goedgekeurde afwijkingen**, expliciet in de test vastgelegd: (1) de overbodige laatste `<br>` onderaan het zakelijk-blok valt weg (core is schoner); (2) de core html-escapet alle waarden (veiliger/correcter; de oude opmaak deed dat niet) — vastgelegd met een speciale-tekens-testgeval. Makelaar wordt nog niet doorgegeven (neutraal, leeg vergeleken). Geen env-var/Railway-actie nodig; geen regressie op de bestaande suites. **Gemerged via PR #7; admin-portal maakt de afspraak-opmaak nu via de core.**
- ✅ **F2.2 Stap 6 (storage)** — de bestand-IO (datamap-detectie + atomic JSON lezen/schrijven) in `storage.py` en `instellingen.py` vervangen door `core.storage` (`vind_data_dir` / `pad_voor` / `laad_json` / `bewaar_json`, tegen tag **v0.2.0**). Lokaal behouden (draait nu op core eronder): de afspraken-CRUD (`sla_afspraak_op`, `haal_op`, `haal_op_outlook_id`, `update`, `annuleer`, `alle_aankomend`) en de settings-logica (defaults, diep-merge, validatie). Het module-`_lock` blijft om de volledige lees-wijzig-schrijf-cyclus heen (core lockt alleen de schrijf zelf). Bestandsnamen (`afspraken.json` / `instellingen.json`) en de atomiciteit gelijk; core checkt dezelfde volume-paden in dezelfde volgorde → op Railway blijft de data op `/app/data/<naam>` staan, **zelfde pad, geen migratie**. Round-trip-test `tests/test_storage_roundtrip.py` (CRUD + settings naar een tijdelijke datamap): 22/22 groen, geen regressie. Geen env-var/secret nodig. Buiten scope: token-persist (`token_persist.json`) in `ms_graph.py` — komt bij de Graph-stap. **Gemerged via PR #8; admin-portal leest/schrijft bestanden nu via de core.**
- ✅ **F2 slotronde (A/B/C) — admin-portal volledig op de core:**
  - **A — Makelaar in de Outlook-afspraak (frictie #9 → opgelost):** `klant['makelaar']` wordt nu doorgegeven aan `core.agenda_format.opmaak_opname`, dus de makelaar verschijnt in de afspraak (bij aanmaken én wijzigen). **Gemerged via PR #9.**
  - **B — Mailopmaak naar de core:** nieuwe core-module **`email_format`** (klant- + admin-mails als pure functies, opgezet zoals `agenda_format`), uitgebracht als **core-tag v0.3.0** (core PR #2). Admin-portal stuurt zijn mails nu via `core.email_format`; de lokale `email_templates.py` is verwijderd. **Gemerged via PR #10.**
  - **C — Microsoft Graph naar de core:** `ms_graph.py` is nu nog slechts een dunne shim over `core.graph_auth` (token ophalen/verversen/persistent + device-code-login) en `core.graph_api` (agenda-CRUD + mail); server.py wijzigt niet. **Gemerged via PR #11** (handmatig, na het zetten van de MS-env-vars + opnieuw inloggen — de core vraagt een bredere scope). Geverifieerd op productie: agenda, afspraak boeken/wijzigen/annuleren, mail, én de makelaar in de agenda-patch.

**Volgende stap:** F2 is klaar; de wachtwoord-fix (frictie #10) is opgelost. **F3 is gestart** (zie hieronder): het eerste online-increment van "Dossier voorbereiden" draait. Openstaand: de resterende "Dossier voorbereiden"-onderdelen (deels Kevins beslissing), het afgesplitste Upload-spoor, **secret-rotatie** (BAG + EP, H8.3) en de bredere platformfases (datalaag, jobs, dashboard — zie H10).

**Fase 3 (F3) — Dossier voorbereiden + Upload als online modules op de core:** 🔧 **bezig.**
- ✅ **Dossier voorbereiden — data verzamelen (PR #13):** route **in de admin-portal** `/voorbereiden` + `GET /api/voorbereiden` halen BAG (core.bag), 3DBAG-gebouwhoogte, voorgevel-oriëntatie, woningtype/VABI-bouwjaarklasse en prijs (core.prijs) op. Module `voorbereiden.py` (geport uit `data_api.py`, leesbron).
- ✅ **Dossier voorbereiden — dossier aanmaken (PR #14, core v0.4.0):** knop "Dossier aanmaken in OneDrive" vult het **VABI-sjabloon** in (`vabi_invuller.py`, op de core-templates — zie hieronder) en maakt het dossier: **OneDrive-map + .epa + Invoerkaart.txt** (core.graph_api.onedrive), **To Do-taak** (core.graph_api.todo) en **optioneel OneNote** (core.graph_api.onenote, alleen als geconfigureerd). De cloud **rekent niet** (geen nta8800) — vult alleen het sjabloon in. **Core v0.4.0** levert de VABI-objectenbibliotheek-templates als package-data (`energiemeneer_core.objectbib`); de `nta8800.exe` is bewust niet in git (gegitignored). 
- ✅ **Onderbouwing in het dossier (PR #15):** het **bewijsdocument** (`bewijsdocument.py`, geport uit `pdf_generator.py`) zet weer een PDF in het dossier met BAG-gegevens, 3DBAG-hoogte (ISSO 82.1), voorgevel-oriëntatie (ISSO 8.3) en een **PDOK-luchtfoto** met voorgevel-pijl — reportlab + Pillow, **géén Playwright** (de Playwright-versie was de BAG-viewer-PDF, die de oude tool al had laten vallen). De Invoerkaart.txt is verrijkt met SnelStart-velden (klant/factuur/omschrijving/prijs).
- ✅ **Automatische dossiervoorbereiding (PR #16; bron-fix PR #22):** een **dagelijkse in-app scheduler** + de knop **"Handmatig synchroniseren"** lezen de aankomende opnames **live uit de Outlook-agenda via de core** (`agenda_sync.lees_opnames`) en bereiden elke opname binnen het venster automatisch voor (zelfde flow). **Idempotent** (VBO-dedup via `voorbereid.json`), **robuust** (elke opname faalt onafhankelijk), **gelogd via core.events**. Ook per opname (`POST /api/dossier/afspraak`). **Bron-fix (PR #22):** las eerst de lokale `afspraken.json` (alleen admin-portal-boekingen) → opnames via aanmeldformulier/Calendly/handmatig werden gemist (0 in het overzicht); nu de live agenda als enige volledige bron.
- ✅ **Multi-user-voorbereiding:** de **afleverlocatie** (default = huidige OneDrive-map) en een veld **toegewezen adviseur** (default = ingelogde gebruiker) zijn instelbaar i.p.v. hardcoded (instellingen-blok `dossier`). Graph-calls draaien nu nog op `/me`; latere overstap (app-rechten / gedeelde bibliotheek) is dan config, geen herbouw.
- ✅ **Dashboard (H6, PR #17):** `/dashboard` toont de **pijplijn** (aankomende opnames + dossier-status, met knoppen "Dossier voorbereiden" en "Handmatig synchroniseren"), het **"hangt op"-overzicht** (per dossier, afgeleid of handmatig), de **technische gezondheid** (BAG/EP/Graph-token + recente fouten uit core.events) en **dossier-detail** (drill-down met gegevens + event-historie). Inclusief **re-prep-detectie**: een afspraak die ná voorbereiding van datum verschuift, krijgt status "verschoven" + een "Opnieuw voorbereiden"-knop (`forceer=`).
- ✅ **Dashboard-verfijning (PR #18/#19/#20):** **OneDrive-deeplinks** (webUrl van de dossiermap, **core v0.5.0** `onedrive.web_url`), klikbare **filter-tegels + tellingen**, **ververs-knop + lichte auto-refresh**, **alleen-openstaande** fouten in de gezondheid, en een **dagcyclus-samenvatting**-kaart. **Weekend-slim venster** (vrijdag → t/m maandag), **luchtfoto-cache** per VBO en een **optionele samenvattingsmail** (standaard uit).
- ✅ **Instellingen-UI (PR #20):** de dossier-instellingen staan nu als nette velden op `/instellingen` (afleverlocatie, standaard adviseur, To Do-lijst, voorbereiden-uren-vooraf, dagcyclus-draaitijd/actief, samenvattingsmail aan/uit, OneNote notitieboek/sectie/sjabloon) — Kevin hoeft geen settingsbestand meer te bewerken. Het `dossier`-blok rijdt mee in de bestaande `POST /api/instellingen`; defaults blijven via diep-merge, validatie ongemoeid.
- ⬜ **Resteert voor "Dossier voorbereiden":** de **VABI-berekening** zelf blijft bewust handwerk bij Kevin (de cloud zet alleen het dossier klaar); OneNote-aanmaak staat klaar maar pas actief als Kevin de notitieboek/sectie/sjabloon-velden invult. Spoor A is daarmee online compleet.
- 🔧 **Upload-module (spoor B) — increment 1 gebouwd (PR #21, core v0.6.0):** een afgerond dossier compleet maken door het **EP-Online-afschrift** automatisch op te halen. Scant de mailbox **alleen-lezen** (afzender `noreply_eponline@rvo.nl`, onderwerp "Afschrift energielabel"), parseert postcode + huisnummer (+ toevoeging) uit de PDF-bijlagenaam en matcht aan een voorbereid dossier; **dubbelzinnig/toevoeging-mismatch → geen match** (frictie #7). Match → PDF in de OneDrive-dossiermap + dossier-status **"afschrift binnen"** (bestaande dashboard-pijplijn); geen match → map "Ongematchte afschriften" + dashboard-melding. Idempotent (`afschriften.json`), robuust per mail, gelogd via core.events. Trigger `POST /api/upload/afschriften` + automatische stap in de dagcyclus. Module `upload.py` is zó opgezet dat **increment 2** erbij past. Zie H7.3.
- ⬜ **Upload-module increment 2 — beschikbaar stellen op de koepel** (richting F6): extern EnergielabelPortaal/koepel + 2FA-uit-mail + portaal-credential (secret) + headless browser = aparte, zorgvuldige verkenning. Nog niets voor gebouwd.
- ⛔ **Veiligheidsregel blijft:** geen secret in code die naar Git gaat (BAG/Graph vallen samen met de core-migratie; EnergielabelPortaal-wachtwoord apart bij het Upload-spoor). Roteren: handmatig door Kevin.

📌 Sinds versie 4.15 bestaat er een levende frictielijst (sectie H6a — Productieve frictie). Bevat 10 punten (#9 makelaar-in-agenda en #10 wachtwoord-wijzigen opgelost, #3 deels; rest open); gebruik als input bij elke prioriteringskeuze.

📌 Sinds versie 4.15 is de schaal-ambitie vastgelegd in sectie H1a — Schaal-horizon (multi-user intern + abonnement voor concullega's). Geen fase, wél input voor architectuur-keuzes (auth, datalaag, hosting, billing).

📌 **Roadmap-volgorde gewijzigd in versie 4.14 (3 juni 2026):** de uitvoeringsvolgorde van F3 t/m F6 is omgegooid. Oude F6 (Intake + Upload als online modules) is opgewaardeerd naar F3, en oude F3 (verhuizing naar eigen hosting) is verschoven naar F6 — pas nadat alle tools draaien en de jobs lopen. Zie H10 voor de volledige tabel en toelichting.

**Aantekeningen voor later (consolidatie):**
- **BAG (`api.bag.kadaster.nl`) is vanaf Railway tijdelijk onbereikbaar** ("[Errno 101] Network is unreachable" — een egress-/routeprobleem, vermoedelijk IPv6; géén code- of logicafout in `core.bag`). Opgevangen (PR #25): elke aanmaak-/verrijkingsflow degradeert nu netjes (dossier wordt altijd aangemaakt met het PDOK-adres; BAG-verrijking is best-effort, `bag_status` onthoudt "onbereikbaar" voor een latere retry). **Te onderzoeken bij eigen hosting / Railway-netwerk:** waarom de route naar Kadaster wegviel en of een vaste IPv4/proxy nodig is. Principe vastgelegd: een externe call (BAG/Graph/To Do) mag een kernactie nooit blokkeren — altijd een nette response + degradatie.
- Docker-waarschuwing tijdens Railway-build: secrets via ARG/ENV in Dockerfile/railway.toml (ADMIN_PASSWORD, EP_ONLINE_KEY, MS_CLIENT_SECRET, MS_REFRESH_TOKEN, OVERHEID_API_KEY, SECRET_KEY). Geen build-fout, maar wel best-practice-schuld. Hoort opgeruimd te worden samen met de secret-rotatie van H8.3.
- ✅ **Mail lézen + bijlagen ophalen** zit nu in de core (**v0.6.0**: `mail.zoek_berichten` + `mail.haal_bijlagen`, alleen-lezen; bron was `outlook_handler.py`). In gebruik door de upload-module (increment 1). Bruikbaar voor increment 2 (2FA-code uit de mail) en een latere opdrachtbevestiging-ophaler.
- Vaste mapnaam-template "straat huisnr, woonplaats" hoort in een aparte format-module (bijv. `dossier_format`), niet in module 6.
- Foto-resize-logica uit de oude Uploadtool moet een nette plek krijgen (mogelijk `core/foto` of als hulpfunctie in de Upload-module).
- To Do-taken afvinken/bijwerken: losse uitbreiding op graph_api/todo wanneer de dossier-status-tracking aan de beurt is.
- Testknop op `/instellingen` die een admin-notificatie stuurt zónder een afspraak in te plannen — spaart tijd bij elke mail-gerelateerde wijziging. Eigen PR, geen onderdeel van de strangler.
- Productie `/instellingen` controleren: vermoedelijk staan de bedrijfsgegevens daar net zo leeg/fout als op de preview vóór de fix. Bij het eerstvolgende productie-bezoek invullen (email, telefoon, website, KvK, BTW).
- ✅ Agenda-opmaak gemigreerd naar `core.agenda_format` (F2 Stap 5, gemerged via PR #7). Resteert: de `ms_graph`-/Graph-aanroepen zelf (latere stap).
- ✅ **Makelaar komt nu terug in de agenda-afspraak** (F2 slotronde A, PR #9): `klant['makelaar']` wordt doorgegeven aan `core.agenda_format.opmaak_opname` → "Makelaar:"-blok in de body, bij aanmaken én wijzigen. Frictie #9 opgelost.
- **WSL/Claude Code brak herhaaldelijk op Kevins Windows** (foutcode `Wsl/0x80070422`) doordat CCleaner de dienst **WSLService** telkens uitschakelde. Directe fix: WSLService op 'Handmatig' zetten (`Set-Service -Name WSLService -StartupType Manual` + `Start-Service`). Blijvende oplossing: CCleaner verwijderen, of z'n automatische run / Health Check / Performance Optimizer uitzetten.
- **Claude Code-toestemmingen op gebruikersniveau** voor ononderbroken doorbouwen — allow: `Bash(*)`, `Edit`, `Write`; deny: `Bash(rm -rf *)`, `Bash(git reset --hard *)`, `Bash(git clean -f*)`. Werkwijze: Kevin verleent zoveel mogelijk toestemming vooraf (zelfstandig branchen / schrijven / committen / branch pushen / PR openen); de harde grens blijft: **niet zelf mergen naar main/productie** — stoppen op een groene PR-preview voor Kevins functionele check + merge-go. (Overweeg dit ook in H0b te verankeren.) Aandachtspunt: `cd`-commando's blijven om veiligheid vragen ondanks de allow-lijst — start Claude Code in de projectmap om dat te vermijden. Klein: `gh` (GitHub CLI) installeren zodat PR's niet via het credential-bestand hoeven.
- **Adres-autosuggest leeft in de browser, niet op de server:** `opdracht.html` doet de PDOK-autosuggest rechtstreeks vanuit de browser (`api.pdok.nl`); er is géén server-endpoint. Dat naar `core.bag.vrij_zoeken` trekken via een nieuw server-endpoint is een nette aparte latere stap.
- **Oude hardcoded BAG- én EP-Online-sleutel staan nu in de git-historie (verbrand):** door Stap 3 (BAG) en Stap 4 (EP) zijn beide fallbacks uit `server.py` verdwenen; roteren bij Kadaster resp. EP-Online + de env-vars bijwerken is urgenter geworden. Hoort bij H8.3.
- **Startpunt voor frictie #7 (huisletter-bug, H6a):** `/api/adres` geeft alleen postcode + huisnummer door, géén huisletter — dat verklaart de 34-vs-34A-bug. Nuttig vertrekpunt zodra #7 wordt opgepakt.
- **EP-fout wordt stil "Geen label" (latente quirk, behouden in Stap 4):** `/api/ep` geeft bij een EP-Online-fout (401/403/500/onbereikbaar) HTTP 200 met een foutenvelop terug, waarna de frontend "Geen label" toont. Bewust gedragsneutraal gehouden; een échte foutmelding tonen i.p.v. stilte is een latere, niet-neutrale verbetering (kandidaat voor H6a).
- **Bredere Graph-scope sinds F2/C (lage prioriteit):** door de overstap op `core.graph_auth` vraagt de admin-portal-MS-app nu de volle core-scope (`Files.ReadWrite Tasks.ReadWrite Notes.ReadWrite Calendars.ReadWrite Mail.Send offline_access`) terwijl alleen agenda + mail wordt gebruikt — ruimer dan strikt nodig. Inperken = least-privilege; vergt een aparte core-keuze (scope parametriseerbaar per tool i.p.v. één vaste `_SCOPE`). Vastleggen, geen haast.
- **F3 "Dossier voorbereiden" — stand van de onderdelen:** ✅ VABI-sjabloon invullen (cloud zet klaar, Kevin rekent in VABI), ✅ OneDrive-dossier (map + .epa + Invoerkaart.txt), ✅ onderbouwing/bewijsdocument-PDF (reportlab + PDOK-luchtfoto, géén Playwright; PR #15), ✅ To Do, ✅ optioneel OneNote, ✅ automatische dossiervoorbereiding (dagelijkse synchronisatie met de live agenda via de core, idempotent, events-logging; PR #16; **weekend-slim venster + luchtfoto-cache + optionele samenvattingsmail, PR #19; bron-fix live agenda PR #22**), ✅ dashboard (pijplijn + hangt-op + gezondheid + detail + re-prep; PR #17; **verfijnd: deeplinks/filters/refresh/open-only/samenvattingskaart, PR #18/#19/#20**), ✅ instellingen-UI voor alle dossier-settings (PR #20), ✅ universele adres-zoekbalk op `/voorbereiden` (PDOK-autosuggest, PR #22). ⬜ Resteert — bewust handwerk — de VABI-berekening. De Playwright-BAG-viewer-PDF is definitief vervallen (onderbouwing zit nu in het bewijsdocument).
- **VABI-templates wonen in de core (v0.4.0, package-data):** `energiemeneer_core/objectbibliotheken/` + accessor `objectbib`. **`EPA_NTA8800.exe` (25MB licentie-binary) is bewust NIET in git** — de root-map `Objectbibliotheken/` is in de core gegitignored; alleen de `.xml`-templates zitten in het pakket. **Aanbeveling:** Kevin hoeft niets te doen voor de templates; mocht de `.exe` ooit per ongeluk gecommit raken, houd 'm dan uit de git-historie.
- **OneNote-aanmaak staat klaar maar is uit** tot Kevin de instellingen `dossier.onenote_notitieboek/_sectie/_sjabloon` invult (anders wordt OneNote netjes overgeslagen, zoals de oude tool die het handmatig deed). **Sinds PR #20 zijn deze drie velden invulbaar op `/instellingen`** (sectie "Dossier voorbereiden" → OneNote).
- ✅ **Wachtwoord wijzigen werkt nu** (frictie #10 opgelost, PR #12): nieuwe lokale module `accounts.py` met gehashte wachtwoorden (stdlib pbkdf2-sha256, random salt) persistent op de volume via `core.storage` (`accounts.json`). Multi-account-klaar (dict gebruiker→hash, vandaag één `admin`). `ADMIN_PASSWORD` is nog slechts de **seed** bij een lege store; daarna is `accounts.json` leidend. Endpoint `POST /api/wachtwoord` + sectie op de instellingen-pagina. Later te verhuizen naar een gedeelde core auth-module (voorbereiding op dashboard-accounts, H1a).

# 0b. Werkwijze — drie rollen, één doel

> Waar H0a vertelt wáár het project staat, vertelt H0b hóé eraan gewerkt
> wordt. Lees beide vooraf: dan weet elke nieuwe chat, elke Claude
> Code-sessie en elke nieuwe collega niet alleen de stand van zaken, maar
> ook wie welke pet op heeft.

Dit platform wordt gebouwd door een driehoek. Geen hiërarchie van baas naar
ondergeschikte, maar drie rollen die elkaar aanvullen en bewaken. Elke rol is
een vangnet voor de volgende: de chat voorkomt dat aan de verkeerde dingen
wordt begonnen, Claude Code voorkomt dat ongeteste of onbesproken code wordt
vastgelegd, en Kevin houdt de eindregie. Wie de prompt typt of in welke
volgorde het loopt, ligt níét rigide vast — de rolverdeling wel.

## De drie rollen

| **Rol** | **Wie/wat** | **Doet** | **Vangnet** |
| --- | --- | --- | --- |
| **Strateeg / gids** | Claude in de chat | Bewaart de strategische context (Meesterbrein-kennis) en het *waarom* achter eerdere keuzes. Stelt plannen op vóór er code is. Formuleert prompts voor Claude Code (Kevin mag dat ook rechtstreeks). Reviewt wat Claude Code rapporteert en biedt alternatieven. | Eerste vangnet — voorkomt dat aan het verkeerde wordt begonnen. |
| **Developer met eigen inzicht** | Claude Code (terminal) | Voert het technische werk uit: lezen, schrijven, testen, committen, pushen. Kent de repo-structuur en de concrete code. Toont diff's vóór akkoord. **Mag en moet eigen, slimmere oplossingen voorstellen** wanneer Kevins of de chat's voorstel niet de beste route is — mits expliciet benoemd wát beter is en waaróm, zodat Kevin bewust kan kiezen. | Tweede vangnet — vraagt akkoord vóór commit/push. |
| **Eigenaar / beslisser** | Kevin | Bepaalt de strategische richting en neemt de eindbeslissingen. Reviewt zowel de plannen van de chat als de uitvoering van Claude Code. Doet de functionele test op de Railway PR-preview en geeft akkoord voor de merge naar productie. | Laatste woord — niets gaat live zonder zijn go. |

De rol "developer met eigen inzicht" is bewust geen "uitvoerder". Claude Code
denkt mee en mag tegenspreken; dat het eigen, betere routes voorstelt is geen
overschrijding maar de bedoeling (zie ook H6a, waar dit principe voor het
oplossen van frictiepunten al staat). Dezelfde rol geldt voor een menselijke
collega-developer (zie ONBOARDING.md).

## Werkstromen — vier varianten, niet rigide

De volgorde hieronder is een richtlijn, geen keurslijf. Kies de lichtste vorm
die bij de taak past.

1. **Grote feature of migratie.** Kevin → plan in de chat → prompt → Claude Code
   → diff + test → akkoord Kevin → commit → preview-test op Railway → merge.
   (Canoniek voorbeeld: F2 Stap 1b, de postcode-vervanging — zie H10.2.)

2. **Vervolgstap binnen lopend werk.** Claude Code rapporteert → Kevin stuurt
   dat door naar de chat → de chat adviseert de vervolgprompt → Kevin plakt die
   → Claude Code voert uit. Een loop die doordraait tot het werk af is.

3. **Kleine bugfix of losse uitvoering.** Kevin gaat direct naar Claude Code,
   zonder tussenstop bij de chat. Claude Code voert uit, Kevin reviewt op de
   PR-preview.

4. **Eigen inzicht van Claude Code.** Ziet Claude Code tijdens het werk iets
   beters, dan benoemt het dat expliciet ("ik stel X voor in plaats van Y,
   omdat …") en wacht op Kevins beslissing. Een triviale verbetering mag het
   meteen meenemen, mits met een heldere melding ("zo geïnterpreteerd: …").

## Niet-onderhandelbaar

- **Geen push naar `main`/`master` zonder akkoord van Kevin** — geldt voor
  Claude Code én voor elke collega.
- **Geen merge naar productie zonder een bewezen functionele test op de
  PR-preview.**
- **Bij twijfel: vraag het. Blokkeer niet, sloop geen werkende code, forceer
  geen merge.** Een open vraag is goedkoper dan een teruggedraaide deploy.
- **Bouw geen deuren dicht** — houd waar het weinig kost rekening met de
  schaal-ambitie (zie H1a Schaal-horizon).

# 1. Visie en hoofddoel

## 1.1 Het platform in één beeld

De Ultieme Tool is geen verzameling losse tools meer, maar één online platform. Kevin logt in op één portal en doet daar al zijn werk: aanvragen binnenhalen, dossiers voorbereiden, opnames verwerken, uploaden, VvE- en adviestrajecten beheren. Één dashboard toont over alles heen wat er draait, wat er faalde, en waar elk dossier in de pijplijn zit. Achter de schermen delen alle functionaliteiten dezelfde bouwstenen en dezelfde data.

> **Eindbeeld in één zin** Kevin opent ’s ochtends de portal: alle dossiers van vandaag zijn al voorbereid, de dossiers van gisteren staan in het portaal, het dashboard is groen, en alles — energielabels, VvE, advies — leeft op één plek onder eigen beheer en eigen domein.

## 1.2 Strategisch hoofddoel

> **HOOFDDOEL** € 1.000.000 netto privévermogen opgebouwd binnen het gestelde tijdsbestek. Pijlers: (1) bedrijfsprocessen maximaal automatiseren → meer productietijd, (2) vrij kapitaal investeren in indexfondsen/aandelen/eventueel crypto, (3) optiehandel-programma ontwikkelen. De rol van het platform binnen dit doel: zoveel mogelijk handwerk wegnemen zodat productietijd vrijkomt, en die tijdwinst structureel maken in plaats van per losse tool.

## 1.3 De vier knelpunten die het platform oplost

Versie 4.0 erkent dat het oorspronkelijke knelpunt (terugzoeken na afmelden) slechts één van vier structurele problemen is die uit de huidige opzet voortkomen:

| **#** | **Knelpunt** | **Hoe het platform dit oplost** |
| --- | --- | --- |
| K1 | Na afmelden onduidelijk welke klant/makelaar bij een adres hoort | Centrale data-laag met VBO-ID als sleutel, doorzoekbaar in de portal |
| K2 | Dezelfde logica (auth, BAG, prijzen, agenda) staat 3–5× gekopieerd over tools | Één gedeeld fundament (energiemeneer-core); elke wijziging één keer |
| K3 | Tools draaien verspreid (2× Railway, 2× lokaal, 1× los script), geen overzicht | Één online portal + één dashboard met status, logs en foutmeldingen |
| K4 | Microsoft-token/auth-problemen keren in elke tool apart terug | Één centrale, persistente auth-laag voor het hele platform |

# 1a. Schaal-horizon — van één gebruiker naar meerdere

Het platform wordt nu gebouwd voor één gebruiker (Kevin). Op termijn wil De EnergieMeneer twee kanten op kunnen schalen:

- **(a) Intern personeel** — meerdere medewerkers binnen De EnergieMeneer met eigen accounts en een rolverdeling (bijvoorbeeld opname-adviseur, admin, boekhouder), elk met eigen rechten op de modules en de data.

- **(b) Concullega's** — andere energieadvies-bedrijven die via een abonnementsvorm gebruik kunnen maken van (delen van) het platform. Dit maakt het platform op termijn een product op zichzelf, niet alleen een interne tool.

**Deze schaal-ambitie heeft nu geen prioriteit en is géén onmiddellijke fase — F1 t/m F8 (H10) blijven ongewijzigd.** Ze staat hier omdat ze nú al architectuur-keuzes raakt die we maken: het is goedkoper om er rekening mee te houden dan om er later op terug te bouwen. Concreet als input voor het ontwerp:

- **Identity-/auth-laag (H4.3):** moet niet vastroesten als één-Kevin-token, maar zó worden opgezet dat multi-user (meerdere accounts, rollen) er later op past.

- **Datalaag (F4):** moet per-tenant scheiding kunnen ondersteunen — data van verschillende bedrijven strikt gescheiden.

- **Hosting (F6):** moet een multi-tenant deployment aankunnen.

- **Pricing/billing-laag:** wordt te zijner tijd een eigen module (Stripe of vergelijkbaar, met een mogelijke koppeling naar SnelStart en het bestaande F8-spoor).

Kortom: bouw geen deuren dicht. Waar een keuze tussen "single-user simpel" en "multi-user-klaar" weinig extra kost, kiezen we bewust de laatste.

> **Account-note (6 juni 2026):** echte accounts (login per medewerker, rollen) komen later, samen met het dashboard. De **wachtwoord-fix in de admin-portal (frictie #10)** is hierop voorbereid: opgezet als een kleine account-/wachtwoordlaag (`accounts.py`, store = gebruiker→hash op de volume) i.p.v. een eenmalige single-user-hack — vandaag één `admin`-account, later uit te breiden naar meerdere accounts en uiteindelijk te verhuizen naar een gedeelde core auth-module. Geen doodlopende weg.

# 2. Bedrijfsprofiel

## 2.1 Persoon en bedrijf

| **Veld** | **Waarde** |
| --- | --- |
| Naam | Kevin Valkenhoff |
| Bedrijf | De EnergieMeneer (eenmanszaak) |
| Vestiging | Den Haag, Nederland |
| KvK | 73181455 |
| E-mail zakelijk | info@de-energiemeneer.nl |
| Website | https://www.de-energiemeneer.nl |
| Functie | EP-W/D & EP-W Maatwerkadviseur |

## 2.2 Certificeringen en normatief kader

| **Item** | **Detail** |
| --- | --- |
| EP-W/B adviseur | Gecertificeerd — basisopname bestaande bouw (9708.2207.2827) |
| EP-W/D adviseur | Gecertificeerd — detailopname & nieuwbouw (8787.6403.1001) |
| Maatwerkadviseur | Gecertificeerd — BRL 9500 MWA-W (5409.4128.8097) |
| Bepalingsmethode | NTA 8800:2024 |
| Opnameprotocol | ISSO-publicatie 82.1, 7e druk 2026 |
| Beoordelingsrichtlijn | BRL 9500-W, bindend 14-10-2025 |
| Registratie / portaal | EP-Online (RVO) / EnergielabelPortaal.nl |

## 2.3 Doelgroep en activiteiten (op prioriteit)

- Energielabels — bestaande bouw (grootste volume)

- Energie-maatwerkadviezen voor VvE’s

- Nieuwe energielabels voor makelaars en beleggers

- Particulier verduurzamingsadvies

## 2.4 Financieel nulpunt

| **Kengetal** | **2025** | **2026 YTD** |
| --- | --- | --- |
| Omzet | € 77.487 | € 34.580 |
| Resultaat | € 61.078 | € 28.529 |
| Netto inkomen | ± € 46.400 | — |
| Vrij beschikbaar | ± € 2.400 | — |

# 3. Platformarchitectuur — de drie lagen

Het platform bestaat uit drie lagen. Van onder naar boven: het fundament (gedeelde bouwstenen + data), de modules (de feitelijke functionaliteiten), en de portal + dashboard (waar Kevin werkt). Elke laag praat alleen met de laag eronder — nooit kriskras.

| **Laag** | **Wat** | **Hoofdstuk** |
| --- | --- | --- |
| **Portal + Dashboard** | Één online werkomgeving + overzicht van status/logs/fouten over alle modules | H5, H6 |
| **Modules** | Energielabel-instroom, dossiervoorbereiding, upload, VvE, advies | H7 |
| **Fundament (core + data)** | Gedeelde bouwstenen (auth, BAG, prijs, agenda) + centrale datalaag | H4 |

## 3.1 Ontwerpprincipes

- **Eén bron van waarheid** — businesslogica (auth, BAG, prijzen, agenda-format) staat exact één keer, in de core. Modules importeren, kopiëren nooit.

- **Modules zijn losjes gekoppeld** — een module mag uitvallen zonder de rest plat te leggen. De portal blijft werken; het dashboard toont de storing.

- **Alles is observeerbaar** — elke actie schrijft een event naar de centrale log (wie, wat, wanneer, resultaat). Het dashboard leest die.

- **Eigen huis** — alles draait op eigen hosting onder eigen domein; geen vendor lock-in, klantdata binnenshuis.

- **Idempotent** — dezelfde operatie twee keer draaien mag nooit dubbele dossiers/afspraken opleveren. VBO-ID als sleutel.

## 3.2 Doelarchitectuur (schematisch)

*Onderstaand schema toont het eindbeeld. De pijlen lopen één kant op: boven leunt op onder.*

┌─ PORTAL (login, één werkomgeving) ───────────────┐

│  Dashboard: status · logs · foutmeldingen      │

└───────────┬────────────────────────┘

  MODULES: instroom · voorbereiding · upload · VvE · advies

└───────────┬────────────────────────┘

  FUNDAMENT: energiemeneer-core + centrale datalaag

# 4. Het fundament — energiemeneer-core + datalaag

Het fundament is de belangrijkste investering. Het bestaat uit een gedeelde codebibliotheek (energiemeneer-core) en een centrale datalaag. Alles erboven wordt er goedkoper en betrouwbaarder door.

## 4.1 energiemeneer-core — gedeelde bouwstenen

Eén Python-package die alle herbruikbare businesslogica bevat. Vandaag staat deze logica 3–5× gekopieerd verspreid over de tools (bewezen: de functie _find_data_dir staat identiek in drie bestanden; maak_todo_taak en de hele auth-laag staan dubbel). De core maakt er één bron van.

| **Module** | **Verantwoordelijkheid** | **Vervangt nu de kopie in** |
| --- | --- | --- |
| graph_auth | Microsoft-token ophalen, verversen, persistent bewaren | Aanmeldformulier + Admin Portal (dubbel) |
| graph_api | Agenda, To Do, Mail, OneDrive, OneNote via Graph | Aanmeldformulier + Dossier voorbereiden + Upload |
| bag | Adres- en pandgegevens (BAG + PDOK) | Alle vier + VvE-tool |
| ep_online | Energielabel-status (EP-Online v5) | Aanmeldformulier + Admin Portal |
| prijs | Prijsmatrix (§2.5 / H9) | Aanmeldformulier + Admin + Dossier voorbereiden |
| agenda_format | Outlook titel/body-opmaak (het “merk”) | Aanmeldformulier + Admin Portal |
| storage | Volume-pad-detectie + atomic JSON/DB-opslag | Aanmeldformulier + Admin (3 kopieën) |
| events | Centrale logging: schrijf event naar datalaag | Nieuw — basis voor dashboard |
| klant | Klantvelden die formulier en portal delen: het factuuradres (`factuuradres_afwijkend` + `factuuradres{straat,huisnummer,toevoeging,postcode,plaats}`, veldnamen = aanmeldformulier) en de helper `factuuradres_van(klant, woonadres)` — de enige plek waar factuuradres-of-woonadres wordt gekozen (**v0.22.x**, 8 sep 2026) | Admin Portal (SnelStart-robot, invoerkaart, Vabi-invuller, Klant bewerken, lead-modal, intake) |

> **Architectuur-afspraak (6 juni 2026) — waar "opmaak/merk" thuishoort.** Eén
> `Meesterbrein` blijft de enige bron van waarheid; er komt **geen apart
> "opmaak"-brein**. "Opmaak/merk" valt uiteen in twee soorten, elk met een
> bestaande plek in de drie lagen:
> - **(a) De merk-laag in de core (Python)** — de gebrande tekst/HTML die de
>   achterkant maakt: `agenda_format` (de Outlook-opname-opmaak, geconsolideerd
>   via F2 Stap 5), met de klantmails (`email_templates`, nu nog lokaal in
>   admin-portal) als natuurlijke **volgende** consolidatie. Dit blijft in de
>   core — geen apart pakket.
> - **(b) De web-UI in de Portal-laag (browser HTML/CSS/JS)** — een gedeelde
>   front-end / design system voor de webpagina's van alle tools. Een reële maar
>   **latere** fase die bij de portal-fusie hoort, niet bij de core.

## 4.2 De centrale datalaag

Één plek waar alle dossiers, afspraken, statussen en events leven. Dit is de evolutie van de eerder ontworpen Centrale Klant-Index, nu als platform-datalaag in plaats van losse index. Sleutel: BAG VBO-ID (uniek in heel Nederland, stabiel tussen alle modules).

✅ **Eerste versie gebouwd (F4, admin-portal PR #24):** twee stores via core.storage — **`klanten.json`** (klantregister) en **`dossiers.json`** (de dossiers). Het dossier is de kern-entiteit; de agenda voedt de store (koppelt opnames). Zie H9.5 voor het volledige datamodel.

Drie kerntabellen:

- **dossiers** — één rij per dossier (sleutel `dossier_id`; VBO-ID/adres-sleutel als index), met **klant-koppeling**, adres, fase (1–13), hangt_op, paden en de gekoppelde agenda-afspraak + mijlpalen. ✅ Gebouwd in F4.

- **events** — append-only logboek: elke statuswijziging met tijd, module en resultaat. Voedt het dashboard. *(Gebouwd in core-module 8. Vast event-formaat: `id`, `tijd` (UTC), `module`, `actie`, `resultaat` ∈ {gelukt, mislukt, in_uitvoering}, `niveau` ∈ {info, waarschuwing, kritiek}, `vbo_id`, `bericht`, `details`. `resultaat` en `niveau` zijn strikt — andere waarden geven een fout — zodat het dashboard betrouwbaar kan filteren en kleuren. Opslag nu als JSONL bovenop storage, achter één interne functie zodat B1 (SQLite/PostgreSQL) later in te schuiven is.)*

- **documenten** — 0..N losse bestandskoppelingen per dossier (opdrachtbevestiging, bewijsdoc, factuur, label).

> **Beslispunt B1 — opslagtechniek bij eigen hosting** Bij eigen hosting vervalt het OneDrive-sync-corruptierisico dat eerder de keuze stuurde. Voorstel: PostgreSQL op de eigen server (robuust, gelijktijdige toegang, vrijwel onbeperkt schaalbaar) in plaats van SQLite. Alternatief: SQLite met WAL als je strikt single-user blijft en het simpel wilt houden. Aanbeveling: PostgreSQL, omdat het platform meerdere modules én later mogelijk een tweede gebruiker moet kunnen dragen.

## 4.3 Één auth-laag (lost K4 op)

De terugkerende token-pijn (“na elke redeploy opnieuw inloggen”, “MS_REFRESH_TOKEN veroudert”) is geen reeks bugs maar één ontbrekende voorziening: een centrale, persistente auth. In het platform leeft de Microsoft-koppeling één keer in graph_auth, met tokens in de centrale datalaag/persistent volume. Alle modules lenen die. Één keer inloggen, overal geldig.

# 5. De Portal — één online werkomgeving

De portal is de webapplicatie waar Kevin op inlogt en al het werk doet. Het vervangt het verspreide werken over losse tools, lokale apps en losse scripts. Draait op eigen hosting onder eigen (sub)domein, bijv. portal.de-energiemeneer.nl.

## 5.1 Wat de portal biedt

- **Toegang** — één login voor alles (geen losse wachtwoorden per tool meer).

- **Modules** — elke module als tabblad/sectie binnen dezelfde omgeving.

- **Zoeken** — één zoekbalk over de hele datalaag (adres, klant, makelaar) → dossier in één klik.

- **Doorklikken** — vanuit een dossier direct door naar OneDrive-map, OneNote, agenda, portaal.

## 5.2 Twee voordeuren, één backend

Het huidige Aanmeldformulier (klant-self-service via Calendly) en het Admin Portal (Kevin voert handmatig in) zijn technisch 80% identiek: beide doen BAG, EP-Online, prijs, Graph-agenda, hetzelfde Outlook-format. Ze worden één backend met twee voordeuren. Een veld ‘bron’ (aanmeldformulier / admin / telefoon / makelaar) houdt bij hoe een opdracht binnenkwam.

> **Wens van Kevin, vastgelegd** De agenda-/afsprakenfunctie van het Aanmeldformulier wordt vervangen door de nieuwere versie uit het Admin Portal (eigen Outlook-slot-grid, klant-portaal met wijzigen/annuleren via token-link, bevestigings-/wijzigings-/annuleringsmails). De Admin Portal is daarmee de basis voor de gefuseerde instroom-module.

# 5a. Het bedrijfsproces — de dossier-levenscyclus

> Deze sectie is de **ruggengraat** van het platform: het echte werkproces van één opdracht, van eerste aanvraag tot afgeronde (betaalde) dossier. Architectuur (H3–H6), modules (H7), datamodel (H9.5) en frictie (H6a) hangen hieraan op. De dashboard-pijplijn (H6) is een *weergave* van dit proces.

## 5a.1 Principe 1 — één keer invoeren, overal hergebruiken (harde regel)

Klant-, adres- en makelaargegevens worden bij de **vroegst mogelijke stap één keer** vastgelegd in het dossier (sleutel = **VBO-ID**) en daarna alleen nog **gelezen of aangevuld** — nooit opnieuw ingevoerd of opgezocht. De koppeling **makelaar ↔ klant ↔ adres** wordt één keer gemaakt en is daarna overal beschikbaar: agenda, opdrachtbevestiging, offerte, factuur (met de makelaar in cc), label en mails. Dit is knelpunt **K1** als harde procesregel: wie iets twee keer moet intypen of opzoeken, raakt een ontwerpfout.

## 5a.2 Principe 2 — een flexibele, data-gestuurde levenscyclus

De levenscyclus is **geen vast aantal stappen** maar een **beheerde lijst** die later vanuit het dashboard aangepast, uitgebreid en herordend kan worden. Elke stap heeft een vast set velden:

| **Veld** | **Betekenis** |
| --- | --- |
| naam | wat er gebeurt |
| eigenaar | wie 'm uitvoert: Kevin / automatisch / klant / extern |
| trigger | wat de stap start |
| klaar-conditie | wanneer de stap af is |
| wacht-op | klant / extern / Kevin / niets |
| status | gebouwd / deels / frictie / nog niks — met link naar de module (H7) of frictie (H6a) |

## 5a.3 De stappen (basis: energielabel, ~13)

| **#** | **Stap** | **Eigenaar** | **Wacht op** | **Status** |
| --- | --- | --- | --- | --- |
| 1 | Lead / aanvraag binnen | klant of Kevin | — | Deels (module Instroom, H7.1) |
| 2 | Offerte uitbrengen + akkoord | Kevin | klant | Nog niks |
| 3 | Klant aanmaken + afspraak inplannen + opdrachtbevestiging | Kevin / automatisch | — | Gebouwd — frictie #2/#4 (bevestiging dubbelop) |
| 4 | Dossier voorbereiden | automatische dossiervoorbereiding (H7.2) | — | ✅ Online: handmatig (knop) én automatisch (dagelijkse synchronisatie met de live agenda) — VABI-sjabloon + OneDrive-dossier + onderbouwing + To Do |
| 5 | Opname op locatie | Kevin | — | Handwerk (status-tracking ontbreekt) |
| 6 | Opname uitwerken (VABI) | Kevin | — | Handwerk |
| 7 | Kwaliteits- / BRL-controle | Kevin | — | Nog niks |
| 8 | Registreren bij EP-Online | Kevin / automatisch | — | Deels — registreren = Kevin; het **EP-Online-afschrift** komt daarna binnen per mail en wordt **automatisch in het dossier gezet** (upload-module increment 1, ✅) |
| 9 | Rapport delen met klant + offerte → factuur | Kevin | klant | Frictie #1 (de oorspronkelijke pijn) |
| 10 | Dossier uploaden (EnergielabelPortaal/koepel) | automatisch (upload-module, H7.3) | — | Online in opbouw: increment 1 (dossier compleet maken — afschrift ophalen) ✅; increment 2 (beschikbaar stellen op de koepel, 2FA/browser) volgt. Oude desktop-Uploadtool blijft tijdelijk leesbron. |
| 11 | Archiveren (OneDrive-archief) | automatisch | — | Deels |
| 12 | Betaling controleren / debiteurenbeheer (SnelStart) | Kevin | klant | Niet gekoppeld |
| 13 | Factuur betaald? → dossier afgerond | automatisch / Kevin | — | Nog niks |

## 5a.4 Productvarianten (overlays)

Eén proces, varianten erbovenop. Elk dossier draagt een **producttype** dat zijn sjabloon kiest; de varianten passen losse stappen aan zonder het proces te splitsen:

| **Producttype** | **Afwijking t.o.v. de basis** |
| --- | --- |
| Maatwerk-particulier | Géén EP-Online-registratie (stap 8) en géén EnergielabelPortaal-upload (stap 10); ander rapport; rest grotendeels gelijk. |
| VvE-maatwerk | Begint met **KvK → adressenlijst** (module VvE-adressen, H7.4) vóór de opname; **meerdere adressen** in één traject; ander rapport. |

## 5a.5 Hoe het dashboard dit toont

*(Eerste versie gebouwd in F3, PR #17; levenscyclus-fases toegevoegd in PR #23 — zie H6.)*

- **Pijplijn-bord:** alle **dossiers** met hun **levenscyclus-fase** (de stappen uit §5a.3). ✅ **Gebouwd (PR #23) + uitgebreid naar de dossier-datalaag (F4, PR #24):** het dashboard leest sinds F4 de **dossier-store** (alle dossiers, fases **1–13**), niet meer puur de live agenda — de agenda-sync voedt de store. Elk dossier toont een fase-kolom + de **klant**. Wat we kunnen weten wordt **automatisch** afgeleid (lead → stap 1, opname → stap 4, voorbereid → stap 5, afschrift binnen → stap 9); de overige stappen zet Kevin **handmatig** vooruit via een dropdown per dossier (persistent op het dossier). **Fase = status:** de korte status (badge/tegels) volgt uit de fase + vlaggen (mislukt/verschoven/afschrift) — niet meer tegenstrijdig. **Precedentie:** de fase = `max(auto, handmatig)`. De kolommen adres / klant / opname / fase zijn **sorteerbaar**. Een dossier kan **handmatig** worden aangemaakt ("Nieuwe klant + dossier") of automatisch uit de agenda ontstaan. (De volledige kanban per producttype is nog een verfijning.)
- **"Hangt op"-overzicht:** welke dossiers wachten en op wie (klant / extern / Kevin / automatisch) — afgeleid van de **wacht-op van de huidige levenscyclus-fase** (principe 2), of handmatig overschreven. ✅ Sinds PR #23 komt de default uit de fase (bv. een te-voorbereiden dossier wacht op de *automatische voorbereiding*, niet op Kevin).
- **Technische gezondheid:** API-status (BAG / EP / Graph-token / secret-verloop), mislukte mails, mislukte jobs — met tijd + oorzaak; opgeloste fouten verdwijnen vanzelf.
- **Dossier-detail:** alle gegevens + documenten + event-historie op één plek.

## 5a.6 Verankering (kruisverwijzingen)

Deze sectie is de ruggengraat; de andere secties verwijzen ernaar zonder elkaar te overschrijven:

- **H6 (Dashboard)** — de pijplijn rendert uit deze stappen.
- **H7 (Modules)** — beschrijft *wie* de stappen uitvoert (Instroom, Voorbereiding, Upload, VvE).
- **H9.5 (Datamodel)** — waar de één-keer-ingevoerde data leeft (dossier op VBO-ID).
- **H6a (Frictie)** — de pijn per stap (o.a. #1 bij stap 9, #2/#4 bij stap 3).
- **Events-tabel (H4.2 / module 8)** — logt gebeurtenissen tegen deze stappen.

# 6. Het Dashboard — één overzicht

Het dashboard is het zenuwcentrum dat Kevin in één oogopslag laat zien hoe het platform ervoor staat. Het leest uit de centrale events-tabel en de modulestatussen.

> **✅ Eerste versie gebouwd (F3, PR #17) — `/dashboard` in de admin-portal.** Toont: (1) **pijplijn** — aankomende opnames met dossier-status (voorbereid / niet / mislukt / verschoven), met knoppen "Dossier voorbereiden" en **"Handmatig synchroniseren"**; (2) **"hangt op"** — per dossier, afgeleid van de status of handmatig gezet; (3) **technische gezondheid** — BAG/EP (env) + Graph-token + recente mislukte events met tijd + oorzaak; (4) **dossier-detail** — drill-down met gegevens, dossiermap en event-historie. Inclusief **re-prep-detectie** (verschoven afspraak → "opnieuw voorbereiden"). **De pijplijn leest de opnames live uit de Outlook-agenda via de core** (`agenda_sync`), aangevuld met de voorbereid-registry + `core.events` (bron-fix PR #22). Multi-user-bewust (adviseur-filter is later config).
>
> **✅ Verfijnd (F3, PR #18/#19/#20):** (a) **OneDrive-deeplinks** — bij het aanmaken wordt de `webUrl` van de dossiermap vastgelegd (core.graph_api.onedrive `web_url`, **core v0.5.0**) en als klikbare link in het dossier-detail getoond; (b) **filters + tellingen** — klikbare tegels (open / voorbereid / mislukt / verschoven) bovenaan de pijplijn; (c) **ververs-knop + lichte auto-refresh** (elke 60s aan/uit) zodat het dashboard geen momentopname is; (d) **technische gezondheid opgeschoond** — alleen nog **openstaande** fouten (een bron die later alsnog lukte verdwijnt automatisch); (e) **synchronisatie-samenvatting** — kaart met "X voorbereid, Y mislukt" uit de laatste synchronisatie (events).
>
> **✅ Centrale dossier-datalaag (F4, PR #24):** het dashboard leest nu de **dossier-store** (`dossiers.json` + klantregister `klanten.json`), niet meer puur de live agenda — de agenda-sync voedt de store. De **klant** staat per regel; er is een knop **"Nieuwe klant + dossier"** en een **klantregister-overzicht**. **De knop is BAG-bestendig (PR #25):** een onbereikbare BAG blokkeert het aanmaken niet meer — het dossier wordt altijd met het (PDOK-)adres + klant aangemaakt, BAG-verrijking is best-effort (`bag_status` voor een latere retry). Daarnaast een read-only sectie **"Dossiers in behandeling"** uit de Microsoft To Do-lijst (core v0.8.0 `todo.lees_taken`; defensief, lege staat bij geen toegang). **Fase = status:** de status volgt uit de fase + vlaggen (geen tegenstrijdigheid meer). De fases lopen nu **1–13** (een lead bestaat al vóór de opname). Bestaande registries netjes gemigreerd (niets kwijt). Zie H9.5.
>
> **✅ Levenscyclus-fases (PR #23):** de pijplijn toont per dossier een **fase-kolom** met de levenscyclus-stappen uit H5a (§5a.3). Auto-detectie van de bekende mijlpalen (te voorbereiden / voorbereid / afschrift binnen) + **handmatige voortgang** via een dropdown per dossier (persistent via core.storage), met precedentie `max(auto, handmatig)`. De kolommen **adres / opname / fase** zijn **sorteerbaar**. Twee fixes meegenomen: robuustere adres-parsing uit de agenda-locatie (met nette placeholder als parsen niet lukt) en een zinnige, fase-afgeleide "hangt op". **Nog te verfijnen:** het volledige kanban-bord per producttype + status-events per stap.

## 6.1 Wat het dashboard toont

| **Onderdeel** | **Inhoud** |
| --- | --- |
| Systeemstatus | Per module: draait / gestopt / fout. API-checks (BAG, EP, Graph-token, client-secret verlooptijd). |
| Foutmeldingen | Actuele storingen met tijd, module en oorzaak; opgeloste fouten verdwijnen automatisch. |
| Logboek | Doorzoekbaar event-log over alle modules (wie/wat/wanneer/resultaat). |
| Pijplijn-overzicht | Welke dossiers in welke fase: voorbereid / opgenomen / klaar voor upload / geüpload / afgerond. |
| Dagcyclus | Resultaat van de 06:00-jobs: X voorbereid, Y geüpload, Z wachten op actie. |

## 6.2 De dagcyclus (06:00)

Twee geautomatiseerde jobs, aangestuurd vanuit het platform en zichtbaar op het dashboard:

> **Naamgeving:** de interne werknamen "Job A" en "Job B" zijn **geretired**. We spreken van **automatische dossiervoorbereiding (met handmatige synchronisatie)** en de **upload-module**. (Het interne endpoint `/api/job-a/run` en de bestandsnaam `job_voorbereiden.py` mogen blijven; de zichtbare labels niet.)

- **Automatische dossiervoorbereiding (met handmatige synchronisatie)** — ✅ **gebouwd (F3, PR #16; bron-fix PR #22):** een dagelijkse in-app scheduler **leest de aankomende opname-afspraken rechtstreeks uit de live Outlook-agenda via de core** (`agenda_sync.lees_opnames` op `core.graph_api.agenda`) en bereidt per opname automatisch het dossier voor (VABI-sjabloon + OneDrive-map + onderbouwing + To Do), idempotent (VBO-dedup) en robuust per afspraak, met logging via core.events. Een opname wordt herkend aan het vaste core-onderwerp ("Energielabel opname"); het adres komt uit de locatie van de afspraak. Ook handmatig te draaien via de knop **"Handmatig synchroniseren"** (`POST /api/job-a/run`, intern) of per opname (`POST /api/dossier/afspraak`). *(Planning-keuze: in-app scheduler i.p.v. Railway-cron, omdat admin-portal één single-instance service is.)* **✅ Verfijnd (PR #19):** (1) **weekend-slim venster** — op vrijdag wordt het venster verlengd t/m eind maandag; (2) **bewijsdocument-cache** — de PDOK-luchtfoto wordt per VBO gecachet; (3) **optionele samenvattingsmail** — na elke cyclus een kort mailtje naar het bedrijfsadres, **standaard uit**. De **draaitijd, het venster, actief-aan/uit en de mail** zijn instelbaar op `/instellingen`.

- **Upload-module (voorheen "Job B")** — een afgerond dossier afhandelen: dossier compleet maken (EP-Online-afschrift ophalen, ✅ increment 1) en daarna beschikbaar stellen op de energielabelkoepel (increment 2, nog niet gebouwd). Zie H7.3.

# 6a. Productieve frictie

Dit is een **levend document**. Frictie die herhaaldelijk wordt gevoeld is een signaal dat een fase of module aandacht verdient. Punten met een geschatte tijd-per-week zijn directe input voor prioritering: hoe meer tijd een irritatie structureel kost, hoe zwaarder die meeweegt. De lijst wordt **bijgewerkt zodra een nieuwe irritatie opvalt**, en een punt wordt **geleegd (verwijderd) zodra het structureel is opgelost** door een fase of PR — niet eerder, want een half opgeloste pijn blijft pijn.

**Belangrijk principe bij het oplossen van deze punten:** Claude (zowel in de chat als in Claude Code) mag en moet eigen, slimmere oplossingen voorstellen wanneer Kevins beschrijving wél het probleem dekt, maar niet noodzakelijk de beste oplossing. Kevin is geen doorgewinterde programmeur en kent niet altijd de elegantste route — een goede inval van Claude of de collega is uitdrukkelijk welkom. **Voorwaarde:** benoem expliciet wát je voorstelt en waaróm het beter is dan Kevins oorspronkelijke beschrijving, zodat hij bewust kan kiezen. De beschrijving in de tabel legt de *pijn* vast, niet de verplichte oplossing.

| **#** | **Beschrijving** | **Frequentie** | **Tijd/week** | **Categorie** | **Lost op in fase** | **Status** |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Bij elke energielabel-afmelding moet ik de bijbehorende klant opzoeken aan het adres, de juiste offerte vinden, omzetten naar factuur en de makelaar opzoeken om in de cc te zetten. | bij elk energielabel | ~10 min per keer | Data/integratie | F4 + F8 | Open |
| 2 | De opdrachtbevestiging is dubbelop met de afspraakbevestiging. | bij elke nieuwe aanvraag | nog invullen | Proces/UI | F3 | Open |
| 3 | Agenda-patch toonde tijden als "0900 en 1030 uur" i.p.v. "09:00 – 10:30". Daarnaast: de eerste afspraak van de dag (09:00) verschijnt als puntsafspraak i.p.v. een blokje met eindtijd. | bij elke nieuwe afspraak | — | Bug (klein) | PR #1 (gedeeltelijk) + later in F3 bij agenda_format-migratie | ✅ Tijdformaat (HHMM→HH:MM) is opgelost in PR #1 op admin-portal (gemerged 3 juni 2026). Puntsafspraak-bug voor 09:00: status nog te bevestigen door Kevin (mogelijk ook opgelost — herziening bij volgende functionele test). |
| 4 | De afspraakbevestiging moet meteen dienen als opdrachtbevestiging. Geldt voor zowel klant-self-service (aanmeldformulier) als handmatig inplannen (admin portal). | bij elke nieuwe aanvraag | nog invullen | Proces | F3 (fusie aanmeldformulier + admin-portal) | Open |
| 5 | Bij woning-beoordeling in de admin portal is StreetView soms onvoldoende. Wens: bovenaanzicht (zoals BAG-viewer) toevoegen. | regelmatig | nog invullen | UI-feature | quick fix (PR) | Open — geschikt voor nieuwe collega |
| 6 | Spoed-aanvinkbox bij afspraak inplannen met melding "+ €35 incl. BTW" wanneer mogelijk. Maakt eerste 48 uur zichtbaar in de agenda (standaard nu als bezette ruimte ingebouwd). | gewenst | nog niet meetbaar | Feature | eigen PR | Open — geschikt voor nieuwe collega |
| 7 | Sommige adressen geven foute resultaten in nieuwe-opdracht-aanvragen, bijv. Stille Veerkade 34 vs 34A → dezelfde gegevens. | onbekend (wel reproduceerbaar) | zelden maar wel data-integriteitsrisico | Bug | onderzoek (huisletter-handling in BAG-koppeling) | Open |
| 8 | Inkomende makelaar-aanvraag via aanmeldformulier vergt nu handmatig overkopiëren: gegevens naar admin-portal voor de agenda, daarna SnelStart voor de boekhouding, daarna opdrachtbevestiging + offerte sturen. | nog invullen | nog invullen | Proces/integratie | F3 + F4 + F8 | Open |
| 9 | Makelaar wordt wel benoemd in admin-portal maar komt niet terug in de agenda-patch. | bij elke makelaar-aanvraag | nog invullen | Bug | F2 slotronde A (PR #9) | ✅ **Opgelost** (6 juni 2026) — `klant['makelaar']` gaat nu via `core.agenda_format.opmaak_opname` naar de Outlook-afspraak (bij aanmaken én wijzigen). |
| 10 | Wachtwoord wijzigen in de admin-portal werkt niet. | onbekend | nog invullen | Bug | losse fix (PR #12) | ✅ **Opgelost** (6 juni 2026) — gehashte, persistente accounts-store (`accounts.py`, pbkdf2 + `core.storage`); `ADMIN_PASSWORD` nog als seed. Multi-account-klaar (zie H1a). |

**Hoe we deze lijst gebruiken**

- Bij elke nieuwe roadmap-sessie controleren of de huidige fase deze pijn adresseert.
- Quick fixes oppakken in losse PR's — niet wachten op grote fases.
- Frictie die níét wordt opgelost door de geplande fases is een signaal om de roadmap te heroverwegen.
- Claude of de collega mag eigen alternatieve oplossingen voorstellen wanneer een betere route mogelijk lijkt; Kevin beslist uiteindelijk.

*De tijd-per-week-kolom is op de meeste punten nog niet ingevuld. Aanvullen zodra meetbaar, zodat prioritering op data gebaseerd kan worden in plaats van op gevoel.*

# 7. De modules — status per functionaliteit

Elke huidige tool wordt geherpositioneerd als module op het platform. Hieronder per module: wat het doet, huidige staat, en wat er nodig is om het in te passen.

## 7.1 Module: Instroom (Aanmeldformulier + Admin Portal, gefuseerd)

Doel: aanvragen binnenhalen — via klant-self-service (formulier + Calendly) én via handmatige invoer door Kevin (telefoon/makelaar). Resultaat: bevestigde afspraak in Outlook + dossier in de datalaag.

| **Aspect** | **Status** |
| --- | --- |
| Aanmeldformulier | Live op Railway (De-Energiemeneer/energiemeneer-aanmeldformulier). 3-staps flow, Calendly-webhook, agenda-patch, polling/monitor/healthcheck. |
| Admin Portal | Live op Railway (De-Energiemeneer/admin-portal). Eigen slot-grid, klant-portaal via token, bevestig-/wijzig-/annuleer-mails. |
| Te doen | Fuseren tot één backend op de core; agenda-functie van formulier vervangen door Admin-versie; bron-veld toevoegen; verhuizen naar eigen hosting. |

## 7.2 Module: Dossier voorbereiden (voorheen "Intake Tool" v4.9)

Doel: per opname automatisch een compleet dossier opbouwen uit BAG, 3DBAG, oriëntatie, bewijsdocument, VABI-template, OneDrive-map, OneNote en To Do-taak.

| **Aspect** | **Status** |
| --- | --- |
| Kern | Werkend, lokaal (Flask op :5000). Voorgeveloriëntatie 95–98%, .epa-generatie, VBO-ID duplicate-detectie. |
| Online (F3) | **Live in de admin-portal** (route `/voorbereiden`): data verzamelen — BAG/3DBAG-hoogte/voorgevel-oriëntatie/woningtype/prijs (PR #13) — én **dossier aanmaken** (PR #14): VABI-sjabloon invullen (core-templates v0.4.0) + OneDrive-map + .epa + Invoerkaart.txt + To Do + optioneel OneNote. Modules `voorbereiden.py`, `vabi_invuller.py`, `dossier.py`. Afleverlocatie + adviseur instelbaar. |
| Te doen | Bewijs-PDF via Playwright (onbewezen op Railway); VABI-berekening blijft handwerk bij Kevin (cloud rekent niet); OneNote actief zodra geconfigureerd; daarna aangestuurd door de automatische dossiervoorbereiding. |

## 7.3 Module: Upload

Doel: een afgerond dossier ("klaar voor uploaden") verder afhandelen. De module heeft **twee increments**, die los gebouwd worden:

1. **Dossier compleet maken** — ontbrekende documenten ophalen en in het dossier zetten. ✅ **Increment 1 gebouwd (PR #21):** het **EP-Online-afschrift** wordt automatisch uit de mailbox gehaald (afzender `noreply_eponline@rvo.nl`, onderwerp "Afschrift energielabel"; alleen-lezen), gematcht aan het juiste dossier op **postcode + huisnummer (+ toevoeging)** en in de OneDrive-dossiermap gezet; de dossier-status wordt **"afschrift binnen"** (zichtbaar in de bestaande dashboard-pijplijn). Geen/ dubbelzinnige match → map "Ongematchte afschriften" + dashboard-melding. Idempotent (`afschriften.json`), robuust per mail, gelogd via core.events. Handmatige trigger `POST /api/upload/afschriften` + automatische stap in de dagcyclus na de dossiervoorbereiding. Steunt op **core v0.6.0** (alleen-lezen `mail.zoek_berichten` / `mail.haal_bijlagen`).
2. **Beschikbaar stellen op energielabelkoepel** voor audits — koepel-login met 2FA + browserrobot. ⬜ **Increment 2: nog niet gebouwd**, krijgt z'n eigen zorgvuldige verkenning (extern portaal, 2FA-uit-mail, portaal-credential als secret, headless browser). De module is zo opgezet dat increment 2 er als tweede stap bijkomt.

| **Aspect** | **Status** |
| --- | --- |
| Online module (`upload.py` in admin-portal) | ✅ Increment 1 (dossier compleet — afschrift) gebouwd; ⬜ increment 2 (koepel) volgt. |
| Leesbron (oude desktop-Uploadtool) | Blijft tijdelijk leesbron voor increment 2: lokaal werkend (Tkinter + Playwright), 8 parallelle threads, verificatie per categorie, foto-compressie. |
| Te doen (increment 2) | Portaal-interactie (Playwright, geen publieke API); 2FA-code uit de mail (core mail-lezen ligt er); status naar datalaag/dashboard. |

## 7.4 Module: VvE-adressen

Doel: op basis van een KvK-nummer een volledig adressenoverzicht van een VvE genereren (via BAG), met postcode- en pariteit-verificatie tegen buurpanden. Basis voor VvE-maatwerkadvies.

| **Aspect** | **Status** |
| --- | --- |
| Kern | Werkend als los CLI-script (vve_adressen.py). KvK → Excel, slimme cluster-parsing, postcode-/pariteit-filtering. |
| Te doen | Eigen KvK/BAG-keys vervangen door core.bag; web-UI in de portal i.p.v. CLI; output koppelen aan datalaag; uitbouwen richting maatwerkadvies-traject. |

## 7.5 Module: Advies (toekomst)

Doel: particulier verduurzamingsadvies en VvE-maatwerkadvies als volwaardige trajecten in de portal. Nu nog niet gebouwd; de VvE-adressenmodule is de eerste bouwsteen. Reserveer plek in datamodel en portal voor advies-dossiers (ander type dan energielabel).

# 8. Infrastructuur en migratie naar eigen hosting

## 8.1 Huidige verspreide situatie

| **Tool** | **Waar het nu draait** | **Repo** |
| --- | --- | --- |
| Aanmeldformulier | Railway (US East) + volume | De-Energiemeneer/energiemeneer-aanmeldformulier |
| Admin Portal | Railway | De-Energiemeneer/admin-portal |
| Dossier voorbereiden (was Intake Tool) | Lokaal Windows (Flask :5000); eerste online-increment als route in admin-portal | lokaal + admin-portal |
| Uploadtool | Lokaal Windows (Tkinter) | lokaal / backend |
| VvE-tool | Los CLI-script | (VvE-repo) |

## 8.2 Doel: eigen hosting onder eigen domein

Keuze (bevestigd): alles binnenshuis, op eigen hosting en eigen domein. Voordelen: geen vendor lock-in, klantdata in eigen beheer, één omgeving, één auth, geen Railway-volume-eigenaardigheden meer.

Aandachtspunten bij migratie (te bewaken):

- HTTPS + eigen (sub)domein voor de portal en de inbound Calendly-webhook.

- Persistente opslag voor tokens, datalaag en dossiers.

- Achtergrondprocessen (polling, monitor, healthcheck, 06:00-jobs) als beheerde services/cron.

- Veilige opslag van secrets (geen hardcoded keys meer — zie H8.3).

- Dezelfde Azure App-registratie kan blijven; alleen redirect-URI / token-locatie verandert.

- De Playwright-gedreven Uploadtool heeft een omgeving met browser nodig (headless Chromium op de server).

## 8.3 Direct te doen: secrets opschonen

> **Veiligheid — met prioriteit** In de huidige repo’s en notities staan API-keys (BAG, EP-Online) hardcoded als fallback en staan MS_CLIENT_SECRET en RAILWAY_TOKEN in platte tekst in werkdocumenten. Bij de overstap naar eigen hosting: alle secrets naar environment variables / een secrets-store, en de oude secrets roteren in Azure en bij de API-leveranciers. Dit is het natuurlijke moment — er wordt toch verhuisd.

## 8.4 Beslispunt B2 — stack-keuze bij fusie

Aanmeldformulier en Admin Portal draaien nu beide op een rauwe Python http.server. De oude Dossier-voorbereiden-tool gebruikt Flask (het eerste online-increment draait nu echter als route in de admin-portal op http.server). Voorstel: bij de fusie alles op Flask zetten zodat de hele backend-stack consistent is en de core-modules overal hetzelfde werken. Alternatief: rauwe http.server samenvoegen (minder migratiewerk nu, maar twee smaken backend op termijn).

# 9. Contracten — de bron van waarheid

Deze sectie bevat de afspraken die de code moet volgen. Verandert er iets hier, dan verandert het op één plek in de core — en daarmee overal. Dit is de acceptatietest bij elke wijziging.

## 9.1 Prijsmatrix energielabels

| **Categorie** | **Bestaande bouw** | **Nieuwbouw (≥2021)** |
| --- | --- | --- |
| Tot 100 m² | € 280 | € 425 |
| 100 – 150 m² | € 315 | € 460 |
| 150 – 200 m² | € 355 | € 500 |
| >200 m² / weet niet | Maatwerk | Maatwerk |
| Spoedtoeslag | + € 30 | + € 30 |

*Alle prijzen incl. BTW. Automatisch bepaald op basis van oppervlakte + nieuwbouwvlag.*

## 9.2 Microsoft Graph — Azure App

| **Veld** | **Waarde** |
| --- | --- |
| CLIENT_ID | 75b57417-b3b0-4d9b-8162-79c36ded82e8 |
| TENANT_ID | 927d1e4a-d007-430e-9091-bc0c34214e3f |
| Scopes | Files.ReadWrite, Tasks.ReadWrite, Notes.ReadWrite, Calendars.ReadWrite, Mail.Send, offline_access |
| Auth-flow | Device Code Flow; tokens persistent in de centrale datalaag/volume |
| Client secret | Verloopt ~november 2027 (alert-systeem actief) |

## 9.3 Outlook-afspraak format (het “merk”)

> **Vaste opmaak — één bron in core.agenda_format** Titel: `[Klantnaam]: Energielabel opname [m²]m² tussen [begin] en [eind] uur` (bijv. "Jan Jansen: Energielabel opname 120m² tussen 15:30 en 17:00 uur"; tijden in Amsterdamse tijd, m² vervalt als de oppervlakte onbekend is, naam valt terug op "Klant onbekend"). Locatie: volledig adres. Duur: 90 minuten. Reminder: 60 min van tevoren. Body: klantnaam, e-mail, telefoon, adres, bouwjaar, oppervlakte, huidig label, woningtype, prijs, makelaar (indien ingevuld), zakelijke gegevens (indien van toepassing), opmerkingen — alle klantinvoer HTML-veilig. Geldt identiek voor alle instroomkanalen — Kevin ziet in zijn agenda altijd hetzelfde overzicht. *(Beslissing 1 juni 2026: titel bewust de bewezen oude-stijl met klantnaam + m² + tijden, i.p.v. de eerdere adres-variant — geeft in de agenda in één oogopslag wie/hoe laat.)*

## 9.4 OneDrive-mappenstructuur

Pad: OneDrive – De Energiemeneer → 1. Werkmap → 1. Energielabels

| **Map** | **Inhoud** |
| --- | --- |
| 1. Archief (3 maanden) | Afgeronde en geüploade dossiers |
| 2. Uitgesteld | Wacht op actie van klant |
| 3. Klaar om te uploaden | Dossiers gereed voor EnergielabelPortaal |
| [Adres-map] | Bijv. ‘Graskopstraat 8, ’s-Gravenhage’ (BRL dossiereis) |

## 9.5 Datamodel — Klant + Dossier als kern-entiteiten

✅ **Gebouwd in F4 (admin-portal PR #24).** De datalaag bestaat uit twee
persistente stores via `core.storage` (`klanten.json` + `dossiers.json`). Het
**dossier** is de kern-entiteit (niet meer de agenda); een **klant** kan meerdere
dossiers hebben. Primaire sleutel van een dossier = een interne `dossier_id`
(een **lead** bestaat al vóór er een VBO-ID is); VBO-ID, de genormaliseerde
**adres-sleutel** en het agenda-event-id zijn match-/dedup-indexen. *(Opslag nu
als JSON via core.storage achter één laag, zodat B1 — SQLite/PostgreSQL — later
in te schuiven is.)*

**Klant** (`klanten.py`) — velden één-op-één uit het aanmeldformulier, zodat
SnelStart later een plug-in is (principe 1):

| **Veldgroep** | **Velden** | **Eigenaar (write)** |
| --- | --- | --- |
| Klant-kern | voornaam, achternaam, e-mail, telefoon | Instroom / handmatig |
| Type + facturatie | `factuur_type` (particulier/zakelijk), `bedrijf` (naam, **KvK**, **BTW**; het oude adresdeel is bij de migratie van 8 sep 2026 naar `factuuradres` overgenomen) | Instroom / handmatig |
| Factuuradres | `factuuradres_afwijkend` (bool, de checkbox "Factuuradres wijkt af van woonadres") + `factuuradres` {straat, huisnummer, toevoeging, postcode, plaats} — los van het factuurtype; definitie in `core.klant`, keuze via `core.klant.factuuradres_van(klant, woonadres)`; sticky (intake overschrijft nooit een portaal-invoer); fail-loud bij vinkje-aan-zonder-adres | Instroom (website) / handmatig (lead-modal, Klant bewerken) |
| Relatie | makelaar (naam, indien doorverwezen), opmerkingen | Instroom / handmatig |

**Dossier** (`dossiers.py`):

| **Veldgroep** | **Velden** | **Eigenaar (write)** |
| --- | --- | --- |
| Identiteit | `dossier_id`, `klant_id` (→ klant), `adres_sleutel`, bron | Datalaag |
| Adres/BAG | straat, huisnr, huisletter, toevoeging, postcode, woonplaats, VBO-ID, pand-ID, bouwjaar, opp | Instroom + Voorbereiding |
| Opname | gekoppelde agenda-afspraak (`event_id`, start, eind, bron) | Agenda-sync |
| Levenscyclus | **fase** (1–13, H5a) = handmatige voortgang + auto-mijlpalen; **hangt_op**; **toegewezen adviseur** | Dashboard / auto |
| Dossier | map-pad (OneDrive), dossier-url, **voorbereid**-mijlpaal (tijd/mapnaam/start), `laatste_prep_resultaat` | Voorbereiding |
| Afsluiting | **afschrift**-mijlpaal (EP-Online: bestand/registratienr), portaal-/factuurvelden (later) | Upload / handmatig |

**Hoe een dossier ontstaat (twee wegen, geen dubbelen):** (1) **handmatig** via
"Nieuwe klant + dossier" (start default op fase 1 = lead); (2) **automatisch** via
de agenda-sync, die elke opname op **adres-sleutel/event-id** aan een bestaand
dossier koppelt (de lead die een afspraak werd) of een nieuw dossier op fase 4
maakt. De voorbereiding en de afschrift-filer **spiegelen** hun mijlpaal naar het
dossier.

**Fase = status:** de korte status (badge/tegels) wordt uit de fase + de vlaggen
(mislukt / verschoven / afschrift) afgeleid — nooit meer tegenstrijdig. Precedentie
van de fase = `max(auto-mijlpaal, handmatig gezet)`.

> **Migratie (F4, eenmalig + idempotent):** de bestaande registries
> (`afspraken.json`, `voorbereid.json`, `afschriften.json`, `dossier_voortgang.json`)
> zijn netjes naar de dossier-store overgenomen — niets kwijt. De oude registries
> blijven als idempotentie-cache voor de prep-/upload-modules.

# 10. Roadmap — fundament eerst, dan platform, dan modules

Deze volgorde wijkt bewust af van de oude roadmap (waar de Klant-Index P2 was en consolidatie nergens stond). De reden: er staat drievoudig-gedupliceerde logica en een structureel auth-probleem onder de motorkap. Elke nieuwe feature die daar bovenop komt, vermenigvuldigt die schuld. Daarom: eerst het fundament leggen, dan pas uitbreiden.

> **Toelichting volgordewijziging (versie 4.14, 3 juni 2026):** verhuizing naar eigen hosting (oude F3) is verschoven naar het einde omdat het een infrastructuur-verandering is zonder directe productiviteitswinst. Eerst alle tools op de core (oude F6, nu F3), dan de datalaag en jobs draaiend krijgen — dat levert de échte tijdwinst voor het hoofddoel. Verhuizing kan daarna in alle rust.

| **Fase** | **Wat** | **Waarom hier** | **Status** |
| --- | --- | --- | --- |
| F0 | Secrets opschonen + repo’s taggen | Veiligheid; natuurlijk moment vóór verhuizing | Direct |
| F1 | energiemeneer-core extraheren (storage, auth, graph, bag, ep, prijs, agenda) | Fundament; maakt al het andere goedkoper; lost K2+K4 op | ✅ Klaar (Modules 1–8, 159/159 tests) |
| F2 | Fusie Aanmeldformulier + Admin Portal op de core | Één instroom-backend, één login, één token; lost K3 deels op | 🔧 Mee bezig (F2.0 klaar, zie H10.2) |
| F3 | Dossier voorbereiden online op de core (Upload-spoor afgesplitst naar een latere fase) | Tools op de core; directe productiviteitswinst voor het hoofddoel | Na F2 — bezig |
| F4 | Centrale datalaag + dashboard (status/logs/fouten) | Overzicht over alles; lost K1+K3 volledig op | 🔧 **Datalaag gebouwd (PR #24)** — dossier + klant als kern-entiteiten; dashboard leest de dossier-store. Resteert: per-tenant scheiding (H1a) + B1-opslagkeuze. |
| F5 | Automatische dossiervoorbereiding + upload online aansturen vanuit platform | De grote tijdwinst, nu op schoon fundament | Na F4 |
| F6 | Verhuizing naar eigen hosting + portal-schil | Infrastructuur-stap zónder directe productiviteitswinst; kan ná alle tools/jobs | Na F5 |
| F7 | VvE-module met web-UI + advies-trajecten | Verbreding naar VvE/advies; volgende omzetstroom | Later |
| F8 | SnelStart-koppeling (Make.com) + EP-Online API v5 | Facturatie- en label-status-automatisering | Te verkennen |

## 10.1 Wat dit oplevert voor het hoofddoel

De tijdwinst zit niet in één moment, maar in alles wat erna goedkoper wordt. Een wijziging die nu 3–5× moet, hoeft straks één keer. De automatische dossiervoorbereiding bouwen op een schoon fundament is sneller en minder bug-gevoelig dan op vijf eilanden. Het platform maakt elke volgende uitbreiding (VvE, advies) een module in plaats van een nieuw eiland — zo blijft de automatisering productietijd vrijspelen richting het hoofddoel.

## 10.2 F2 — voortgang in onderdelen

**F2.0 Installeerbaar maken (1 juni 2026):** pyproject.toml in de core gevuld met tzdata-dependency (msal niet nodig — graph_auth regelt tokens zelf via requests). Setuptools als builder. Schone-venv-test geslaagd: pip install . in verse venv, alle imports werken, tzdata bewijst Amsterdamse tijdzone-conversie (UTC 13:30 → AMS 15:30 +zomertijd), geen testbestanden in site-packages.

**Stap 1a — plumbing bewezen op Railway (1 juni 2026):** de admin-portal neemt `energiemeneer-core` als dependency op (via publieke GitHub-tag, anoniem bereikbaar zonder credentials). PR-environment `admin-portal-pr-1`: Nixpacks-build slaagde, `energiemeneer-core 0.1.0` schoon geïnstalleerd, healthcheck groen, `/healthz`-endpoint geverifieerd in de browser ("ok"-response). Hiermee is de leidingenloop bewezen vóór er functionaliteit verschoof. Volgende: stap 1b — postcode-vervanging in `server.py`.

### F2.1 — Railway PR Previews als veiligheidsmechanisme

Voor alle services binnen project helpful-manifestation (admin-portal, en straks ook andere) is in Railway PR Environments aangezet (Project Settings → Environments → 'Enable PR Environments'). Base environment: 'No base environment' (Railway pakt automatisch production-variabelen). Focused PR Environments is UITGEZET na eerste test (zie ontdekking hieronder).

Werkwijze voor élke strangler-stap vanaf nu:
1. Branch maken in Claude Code, pushen naar GitHub
2. Pull Request openen op GitHub (base: main, compare: feature-branch)
3. Railway maakt automatisch PR-environment aan (admin-portal-pr-N)
4. Build + healthcheck draaien in PR-environment — productie wordt niet aangeraakt
5. Pas na groen vinkje + functionele check op de preview-URL: PR mergen naar main → Railway deployt naar productie
6. PR sluiten → Railway ruimt PR-environment automatisch op

Ontdekking: 'Focused PR Environments' (credit-besparende feature die alleen geraakte services deployt) markeerde de admin-portal-service bij PR #1 als 'Not affected by PR' terwijl er wel relevante wijzigingen waren (requirements.txt, tests/, CLAUDE.md). Work-around: handmatig op 'Deploy' klikken op de service-card binnen de PR-environment. Definitieve oplossing: Focused PR Environments UITgezet (geen verspilling want momenteel maar 1 service per project). Bij meerdere services later: heroverwegen of Watch Paths (*.py, requirements.txt, railway.toml) een betere route is.

### F2.2 — Strangler-discipline (geleerde patronen)

De eerste functie in de admin-portal is vervangen door een core-aanroep (postcode-normalisatie, stap 1a/1b — 1 juni 2026, gemerged naar main). Tijdens stap 1b zijn de volgende werkpatronen bevestigd of ontdekt — bewaar als richtlijn voor toekomstige strangler-stappen.

1. **Splits 1a/1b per stap:** plumbing eerst (dependencies + tests, géén gedragsverandering, branch + PR + preview-build), daarna pas gedragsverandering (de eigenlijke vervanging). Niet mengen in dezelfde commit-historie.

2. **'Bevroren ijkpunt'-test:** in de admin-portal-test staat een kopie van de oude lokale logica ingebakken. Ook nadat de echte lokale code uit `server.py` is, blijft de test bewaken dat de core hetzelfde doet als wat de portal vroeger deed. Dit patroon hergebruiken voor toekomstige migraties.

3. **Hardcoded vs persistent instellingen:** bedrijfsspecifieke data (email, telefoon, KvK) hoort in `/instellingen` (persistent op disk), niet in code-defaults. Code-defaults blijven leeg óf bevatten alleen veilige fallback-waarden. Na merge: productie `/instellingen` apart controleren — staat vermoedelijk hetzelfde als wat de preview toonde vóór de fix.

4. **Bonus-fixes mogen mee in een strangler-PR** — mits ze klein en geïsoleerd zijn (één regel, één concept). Grotere vondsten krijgen een eigen PR. Bij twijfel: splitsen voor een schone historie.

5. **Mergen vanuit Claude Code** (`git merge --no-ff` + push naar main, eventueel met `gh` CLI om de PR netjes te sluiten) werkt prima — bespaart browsertabs. Discipline blijft: mergen pas na Kevins expliciete akkoord na preview-test.

## 10.3 F3 — inventarisatie (verkenningsfase, 3 juni 2026)

F3 ("Dossier voorbereiden + Upload als online modules op de core") is verkend vóór
er code beweegt. Conclusie: F3 is geen één-tool-klus maar twee sporen van
verschillende aard en risico.

> **Voortgang (7 juni 2026):** Spoor A (**Dossier voorbereiden**, voorheen "Intake
> Tool") draait online als **route in de admin-portal** (F3.4). Gebouwd + gemerged:
> data verzamelen (PR #13) én **dossier aanmaken** (PR #14) — VABI-sjabloon invullen
> (op de core-templates, core **v0.4.0**/`objectbib`), OneDrive-map + .epa +
> Invoerkaart.txt (F3.3 ✅), To Do, optioneel OneNote. De cloud **rekent niet**
> (geen nta8800; VABI-berekening blijft handwerk bij Kevin) — F3.5 daarmee
> ingevuld als "cloud vult sjabloon, mens rekent". Afleverlocatie + toegewezen
> adviseur instelbaar (multi-user-voorbereiding). Resteert in spoor A: bewijs-PDF
> via Playwright. **Spoor B (Upload) is afgesplitst** naar een eigen latere fase
> (richting F6) — extern portaal + 2FA + credential + headless browser vragen een
> aparte verkenning.

**Twee tools, twee karakters:**
- **Dossier voorbereiden** (voorheen "Intake Tool", ~3.800 regels, Flask) is web-native: relatief tam om online te
  brengen. Schrijft nu bestanden rechtstreeks naar de Windows-OneDrive-map — dat
  moet om naar uploaden via core.graph_api. Bevat unieke IP (voorgevel-oriëntatie,
  3DBAG, VABI-.epa, bewijs-PDF) die nergens anders bestaat. Aandachtspunt: VABI
  vereist nu een lokale installatie (templates in AppData) — online draaien is
  daardoor niet vanzelfsprekend.
- **Uploadtool** (~4.700 regels, Tkinter + Playwright) is een desktopprogramma met
  browser-robot. Kan niet zonder browser-automatisering (er is geen portaal-API).
  Hogere complexiteit: headless Chromium op Railway nog te bewijzen, 2FA-code wordt
  uit de mail gevist, de Tkinter-schil moet eraf.

**Grootste core-winst:** béide tools hebben een eigen kopie van ms_graph.py (662
regels) — samen met aanmeldformulier en admin-portal vier kopieën van dezelfde
auth/Graph-logica. Vervangen door core.graph_auth/graph_api is de grootste,
veiligste opbrengst. Verder direct vervangbaar: bag, prijs (v0.2.0), storage,
events, agenda_format.

> **⛔ Veiligheidsregel F3 — een principe, geen losse voorafgaande stap.**
> De regel: **er gaat geen tool-code naar een Git-repo met een hardcoded secret
> erin.** Eenmaal in de Git-historie krijg je een secret er nooit meer schoon
> uit. Concreet valt dit zo uiteen:
> - **BAG-sleutel (Dossier voorbereiden, `data_api.py`):** verdwijnt automatisch in **F3.2** —
>   daar vervangt de migratie de lokale BAG-logica door core.bag, dat al via een
>   env-var werkt. Geen aparte sanering nodig.
> - **Graph-auth (beide tools, `ms_graph.py`):** verdwijnt bij de
>   ms_graph → core.graph_auth-migratie — **F3.2** (Dossier voorbereiden) en **F3.8** (Upload).
>   Geen aparte sanering.
> - **EnergielabelPortaal-wachtwoord (Upload, `config.py`):** zit NIET in de core
>   (uniek aan de Uploadtool, er is geen portaal-API). Moet apart naar een
>   env-var; hoort bij het Upload-spoor (rond **F3.6/F3.8**).
> - **Roteren van alle drie:** los van de code-volgorde, handmatig door Kevin
>   (deze week). De oude secrets zijn immers al bekend/"verbrand", ongeacht de
>   technische oplossing.
>
> Kortom: de poort blokkeert niet de *start* van F3, maar bewaakt elke
> afzonderlijke repo-push. Voor BAG en Graph valt naleving samen met de
> core-migratie zelf; alleen het portaal-wachtwoord vraagt een eigen
> env-var-actie. Zie ook H8.3.

**Sub-stappen (raming ~9–11), in 1a/1b-discipline net als F2:**

| Stap | Spoor | Inhoud |
| --- | --- | --- |
| F3.0 | gezamenlijk | Inventarisatie (deze sectie) — ✅ klaar |
| F3.1 | gezamenlijk | **Veiligheidsregel (principe, geen losse stap):** geen secret in code die naar Git gaat. Naleving valt voor de BAG-sleutel en Graph-auth samen met de core-migratie (F3.2 / F3.8); alleen het EnergielabelPortaal-wachtwoord vergt een aparte env-var-actie (F3.6 / F3.8). Roteren van de secrets: handmatig door Kevin, los van de code-volgorde. |
| F3.2 | A — Dossier voorbereiden | Core-overlap wegstrangleren: eigen ms_graph → core.graph_auth/graph_api, bag → core.bag, prijs → core.prijs, logging → core.events |
| F3.3 | A — Dossier voorbereiden | Output ombouwen: van rechtstreeks naar de Windows-map schrijven naar uploaden via core.graph_api |
| F3.4 | A — Dossier voorbereiden | Online vorm geven (knop in admin-portal óf aparte Flask-service) + aanpak voor lange taken |
| F3.5 | A — Dossier voorbereiden | VABI-beslissing uitvoeren (lokaal/handmatig houden, meeleveren, of zonder VABI-installatie onderzoeken) |
| F3.6 | B — Upload | GUI ontkoppelen: van Tkinter-venster naar een aanstuurbare service/CLI (kern blijft, schil eraf) |
| F3.7 | B — Upload | Playwright op Railway bewijzen (proef met headless Chromium) — of besluiten dit naar F6 te schuiven |
| F3.8 | B — Upload | Core-overlap wegstrangleren (idem ms_graph → core, bag, logging) |
| F3.9 | B — Upload | Verificatie-per-categorie + parallelle uploads + foto-compressie online betrouwbaar; status naar core.events/dashboard |

**Open beslispunten voor Kevin** (volledige opties + impact in het
verkenningsrapport): secrets-volgorde, vorm van Dossier voorbereiden (knop vs. aparte service — **gekozen: route in admin-portal**),
vorm/timing van Upload (Railway nu vs. F6 vervroegen), Dossier-voorbereiden-output, VABI online,
lange-taken-mechanisme, gedeelde vs. losse auth-tokens, stack-keuze (B2).

Werkvolgorde: éérst F3.1 naleven, dán per spoor een eigen mini-plan — niet de
hele lijst in één keer doorrazen. Spoor B (Upload) verdient mogelijk een eigen
verkenning vóór er code beweegt.

# 11. Versiehistorie

| **Versie** | **Datum** | **Wijziging** |
| --- | --- | --- |
| 3.0 | Mei/Juni 2026 | §7 bijgewerkt na voltooiing uploadtool; voorbereiding samenvoeging. |
| 3.1 | 28 mei 2026 | Admin Portal als vierde pijler toegevoegd (§10); VvE-tool toegevoegd aan project. |
| 4.0 | 28 mei 2026 | Fundamentele herstructurering naar platform-document. Einddoel (één online portal + dashboard, eigen hosting, modules op gedeeld fundament) als uitgangspunt i.p.v. historische pijlers. Nieuwe driedeling architectuur/modules/contracten/roadmap. energiemeneer-core, centrale datalaag, dashboard, fusie instroom, en gefaseerd migratiepad (F0–F8) toegevoegd. Vier structurele knelpunten (K1–K4) benoemd. VvE en advies als modules gepositioneerd. |
| 4.1 | 28 mei 2026 | Bestandsnaam vastgezet op `Meesterbrein.md` (geen versienummer meer in de naam). Versiebeheer-instructie toegevoegd. |
| 4.2 | 28 mei 2026 | Bouwstatus-sectie (H0a) toegevoegd: core-modules 1–4 klaar en getest, module 5 (graph_auth) is de volgende. Versiebeheer-instructie aangescherpt voor toekomstige chats. |
| 4.3 | 28 mei 2026 | Module 5 (graph_auth) klaar en getest (13/13): public client, refresh-rotatie in token_persist.json, onafhankelijke ntfy-noodmelding bij verlopen koppeling (max. 1×/24u). Bouwstatus bijgewerkt; module 6 (graph_api) is nu de volgende. |
| 4.4 | 29 mei 2026 | Module 6 (graph_api) opgezet als subpackage (bestand per onderwerp) met gedeeld _client-loket (token via graph_auth + 401-herstel). Onderdeel 1 agenda klaar en getest (15/15): generieke afspraak-CRUD, opmaak bewust uitgesteld naar Module 7. Volgende onderdelen: mail, onedrive, todo, onenote. |
| 4.5 | 29 mei 2026 | Module 6 onderdeel 2 mail klaar en getest (6/6): generieke stuur_mail (ontvanger/cc/bcc/reply-to als adres of lijst, HTML-body, opslaan-in-verzonden), geen vaste afzender/opmaak. Genoteerd voor later: mail lézen + bijlagen ophalen voor Job B/Uploadtool. |
| 4.6 | 29 mei 2026 | Module 6 onderdeel 3 onedrive klaar en getest (11/11): generieke maak_map (met _1/_2-logica, geen ingebakken mapnamen) en upload_bestand met automatisch veiligheidsnet voor grote bestanden (>4 MB via upload-sessie in stukjes). Loket uitgebreid met rauwe-bytes-upload (put_inhoud). Aantekeningen voor later toegevoegd: vaste mapnaam-template hoort in aparte format-module (dossier_format); foto-resize uit oude Uploadtool moet nette plek krijgen. |
| 4.7 | 29 mei 2026 | Module 6 onderdeel 4 todo klaar en getest (7/7): generieke maak_taak (lijst zoeken of aanmaken, _1/_2-logica bij dubbele taaknaam, optionele deadline DD-MM-YYYY → Amsterdam). Geen ingebakken lijstnamen. Genoteerd voor later: taken afvinken/bijwerken als losse uitbreiding bij dossier-status-tracking. |
| 4.8 | 1 juni 2026 | Module 6 onderdeel 5 onenote klaar en getest (12/12) — daarmee is graph_api volledig af (51/51 tests). Generieke kopieer_sjabloonpagina: notitieboek-, sectie- en sjabloonnaam losgemaakt tot parameters (geen ingebakken "De Energiemeneer"/"Opnames"/"Adres" meer). Twee fragiliteiten opgeschoond: (1) async copyToSection wacht nu op de operatie-statuslink i.p.v. een blinde sleep + gokken welke pagina de kopie is; (2) ontbrekende sjabloon geeft standaard een duidelijke fout — een lege pagina wordt alleen op expliciet verzoek (maak_lege_bij_ontbreken=True) aangemaakt, geen stille fallback meer. Volgende: Module 7 (agenda_format). |
| 4.9 | 1 juni 2026 | Module 7 (agenda_format) klaar en getest (17/17) — **daarmee is de hele core (Modules 1–7) af: 143/143 tests groen.** Vaste Outlook-opmaak losgekoppeld van de generieke agenda-laag: pure functie opmaak_opname levert titel + HTML-body + locatie + herinnering; agenda weet *hoe*, agenda_format weet *wat*. Klantinvoer wordt HTML-veilig gemaakt. H9.3-titel gelijkgetrokken met de gekozen oude-stijl (klantnaam + m² + Amsterdamse tijden) i.p.v. de eerdere adres-variant. Fundament-fase F1 afgerond; volgende fase is F2 (instroom-tools op de core trekken). |
| 4.10 | 1 juni 2026 | Module 8 (events) toegevoegd aan de core en getest (16/16) — totaal 159/159. Centrale append-only logging als fundament voor het dashboard (H6): schrijf_event + lees_events (filters op module/vbo_id/resultaat/niveau/sinds/limiet, nieuwste eerst), bovenop storage als JSONL. Vast event-formaat vastgelegd in H4.2; resultaat (gelukt/mislukt/in_uitvoering) en niveau (info/waarschuwing/kritiek) zijn strikt — geen vrije tekst — zodat het dashboard betrouwbaar kan filteren/kleuren. Opslag achter één interne functie, zodat beslispunt B1 (echte DB) later in te schuiven is. |
| 4.11 | 1 juni 2026 | F2.0 afgerond — energiemeneer-core is nu installeerbaar als Python-package via pip (energiemeneer-core @ git+...). pyproject.toml uitgebreid met tzdata-dependency. Schone-venv-test bewees correcte installatie inclusief Amsterdamse tijdzone-conversie. Bevinding vastgelegd: Railway-GitHub-app heeft 'All repositories'-toegang op het Keviniom-account, dus geen extra configuratie nodig voor F2.1. Volgende: F2.2 — eerste functie in admin-portal door core-aanroep vervangen (strangler-aanpak). |
| 4.12 | 1 juni 2026 | F2 gestart en eerste plumbing-stap (1a) bewezen op Railway. PR Environments aangezet in Railway Project Settings voor automatische preview-deployments per Pull Request. Branch core-integratie-stap1a → PR #1 op admin-portal-repo → PR-environment admin-portal-pr-1: Nixpacks-build slaagde, energiemeneer-core 0.1.0 schoon geïnstalleerd vanaf publieke GitHub-tag (anoniem bereikbaar zonder credentials), healthcheck groen, /healthz endpoint geverifieerd in browser. Werkwijze voor alle toekomstige strangler-stappen vastgelegd in nieuwe sectie F2.1. Ontdekking: 'Focused PR Environments' markeerde service als niet-geraakt (work-around: handmatige Deploy; definitief opgelost door Focused uit te zetten — werkt prima met 1 service per project). Aantekening toegevoegd: Docker-warning over secrets in ARG/ENV hoort bij secret-rotatie H8.3. Volgende: stap 1b — postcode-vervanging in server.py, opnieuw via PR-flow. |
| 4.13 | 1 juni 2026 | F2 Stap 1b (postcode-vervanging) gemerged naar main — admin-portal draait nu in productie op core.bag.normaliseer_postcode. Bonus-oogst meegenomen in dezelfde PR: (a) domein-typo overal gefixt naar de-energiemeneer.nl met streepje (instellingen.py, email_templates.py, klant_portaal.html), (b) agenda-titel toont nu netjes 'HH:MM en HH:MM uur' met dubbele punten in plaats van 'HHMM en HHMM uur'. Nieuwe sectie F2.2 toegevoegd met geleerde patronen (1a/1b-splitsing, bevroren ijkpunt-test, hardcoded vs persistent instellingen, bonus-fix-regel, merge-vanuit-Claude-Code). Aandachtspunten toegevoegd: testknop bouwen, productie-instellingen checken, agenda-format-migratie als latere strangler-stap. Volgende: F2 Stap 2 — bereken_prijs op de core trekken volgens hetzelfde patroon. |
| 4.14 | 3 juni 2026 | Strategische roadmap-wijziging — uitvoeringsvolgorde van F3-F6 omgegooid op verzoek van Kevin. Intake + Upload online modules (was F6) opgewaardeerd naar F3 omdat het directe productiviteitswinst levert. Verhuizing naar eigen hosting (was F3) verschoven naar F6 — pas nadat alle tools draaien en jobs lopen. Hernummering: oude F3↔F6 omgewisseld; F4, F5, F7, F8 ongewijzigd. Alle interne kruisverwijzingen in het document gelijkgetrokken. Korte toelichting boven H10-tabel toegevoegd. |
| 4.15 | 3 juni 2026 | **Twee toevoegingen.** (1) Nieuwe sectie H6a — Productieve frictie: levende lijst van 9 dagelijkse irritaties uit Kevin's werk, gecategoriseerd (bug / proces / UI-feature / data-integratie) en gekoppeld aan welke fase ze structureel oplost. Twee punten (bovenaanzicht in admin-portal, spoedbox bij afspraak) gemarkeerd als geschikt voor de nieuwe collega. Tijdformaat-bug (HHMM→HH:MM) uit PR #1 erkend als opgelost; puntsafspraak-bug voor 09:00 nog te bevestigen. Belangrijk toegevoegd principe: Claude en collega mogen eigen slimmere oplossingen voorstellen bij het oplossen van punten — Kevin's beschrijving dekt het probleem, niet noodzakelijk de beste oplossing. (2) Nieuwe sectie H1a — Schaal-horizon: schaal-ambitie vastgelegd (multi-user voor intern personeel met rollen, en abonnementsvorm voor concullega's). Expliciet géén fase en geen wijziging aan F1–F8, maar input voor architectuur-keuzes die nu al spelen: multi-user auth-laag, per-tenant datalaag (F4), multi-tenant hosting (F6) en een toekomstige pricing/billing-module (Stripe, mogelijke SnelStart-koppeling). |

| 4.16 | 3 juni 2026 | **Werkwijze expliciet vastgelegd in drie bestanden.** Nieuwe sectie H0b — Werkwijze (drie rollen, één doel): de samenwerkingsdriehoek tussen Claude in de chat (strateeg/gids), Claude Code (developer met eigen inzicht) en Kevin (eigenaar/beslisser), met een rollentabel, vier niet-rigide werkstromen en de niet-onderhandelbare regels (geen push naar main zonder akkoord, geen merge zonder bewezen preview-test, bij twijfel vragen, geen deuren dichtbouwen). CLAUDE.md uitgebreid met "Jouw rol als Claude Code" (developer met eigen inzicht, mag/moet slimmere oplossingen voorstellen, strategie via Kevin). ONBOARDING.md §3 uitgebreid met de driehoek en de plek van de nieuwe collega (óók developer met eigen inzicht). Kruisverwijzingen naar H6a (eigen-inzicht-principe) en H1a (bouw geen deuren dicht) i.p.v. duplicatie. |

| 4.17 | 3 juni 2026 | **F3 verkend (Stap 0) en vastgelegd.** Nieuwe sectie H10.3 — F3-inventarisatie: beide lokale tools (Intake Tool ~3.800 regels Flask; Uploadtool ~4.700 regels Tkinter + Playwright) doorgelicht. Conclusie: F3 is twee sporen van verschillende aard — Intake (web-native, lager risico) eerst, daarna Upload (desktop + browserrobot, hoger risico). Grootste core-winst: vier kopieën van ms_graph.py vervangen door core.graph_auth/graph_api. Negen sub-stappen (F3.0–F3.9) opgenomen in 1a/1b-discipline. **Veiligheidsregel vastgelegd als principe — geen secret in code die naar Git gaat:** voor de BAG-sleutel en Graph-auth valt naleving samen met de core-migratie (F3.2/F3.8), alleen het EnergielabelPortaal-wachtwoord vergt een aparte env-var-actie; roteren doet Kevin handmatig, los van de code-volgorde. H0a Bouwstatus bijgewerkt: F3 als "verkend, volgende = F3.2". Versie 4.16 → 4.17. |
| 4.18 | 5 juni 2026 | **Org-verhuizing GitHub: `Keviniom` → `De-Energiemeneer`.** Alle repo's zijn van het persoonlijke GitHub-account `Keviniom` naar de organisatie `De-Energiemeneer` verhuisd. Repo-verwijzingen (clone-URL's, repo-namen) in Meesterbrein.md en ONBOARDING.md bijgewerkt naar `De-Energiemeneer/…`. Git-remotes van de lokale repo's omgezet (energiemeneer-core, admin-portal); de core-pin in de Intake Tool en in admin-portal bijgesteld naar `git+https://github.com/De-Energiemeneer/energiemeneer-core.git@v0.2.0` (admin-portal via PR, dat deployt). **Bewust ongemoeid gelaten:** verwijzingen naar het Railway-account 'keviniom' (dat is niet meeverhuisd) en de historische versiehistorie-regels — die beschrijven de situatie van toen en blijven correct. Versie 4.17 → 4.18. |
| 4.19 | 5 juni 2026 | **F2 Stap 2 (prijs) afgerond en gemerged.** `bereken_prijs` in admin-portal `server.py` vervangen door een dunne adapter rond `core.prijs.bereken_prijs` + `core.prijs.is_nieuwbouw` (tegen tag v0.2.0); output-vorm `{prijs, maatwerk, label}` en de quirk (onbekend type → Maatwerk) behouden. Lokale `PRIJSMATRIX`-duplicaat én het ongebruikte, admin-gated `/api/prijzen`-endpoint verwijderd; `/api/prijs` (live berekening) blijft. Spoedtoeslag bewust ongemoeid (gedragsneutraal). Pariteitstest verbeterd: importeert nu de échte `server.bereken_prijs` en vergelijkt met de bevroren oude logica (`_OUD_*`), groen in een kale omgeving zonder secrets (334/334). Gemerged via PR #4; productie rekent prijzen nu via de core. H0a bijgewerkt (Stap 2 ✅, volgende = Stap 3: `bag_lookup` → `core.bag`). **Twee consolidatie-aantekeningen toegevoegd:** (1) WSL brak herhaaldelijk (`Wsl/0x80070422`) doordat CCleaner WSLService telkens uitschakelde — fix WSLService op 'Handmatig', blijvend CCleaner's auto-run uitzetten/verwijderen; (2) Claude Code-toestemmingen op gebruikersniveau voor ononderbroken doorbouwen (allow `Bash(*)`/`Edit`/`Write`, deny `rm -rf`/`git reset --hard`/`git clean -f`) met de harde grens 'niet zelf mergen', plus aandachtspunten (`cd` vraagt nog steeds → start in projectmap; `gh` installeren). Versie 4.18 → 4.19. |
| 4.20 | 6 juni 2026 | **F2 Stap 3 (bag) afgerond en gemerged.** `bag_lookup` in admin-portal `server.py` vervangen door een dunne adapter rond `core.bag.zoek_adres` (tegen tag v0.2.0); het `/api/adres`-contract exact behouden (`{ok: true, ...velden...}` / `{error: ...}`). Lokale `bag_lookup`-duplicaat én de hardcoded BAG-fallback-sleutel verwijderd — `core.bag` eist `OVERHEID_API_KEY` strikt via env-var (geen fallback meer), die staat nu op Railway (preview + productie). Volledige-pariteitstest `tests/test_adres_pariteit.py`: bevroren verbatim-kopie van de oude `bag_lookup` vs de nieuwe adapter tegen identieke gemockte BAG-JSON; groen incl. kale omgeving (5/5), geen regressie (prijs 334/334, postcode 6/6). Huisletter-bug (frictie #7) bewust niet aangeraakt — gedragsneutraal. Gemerged via PR #5; productie zoekt adressen nu via de core. H0a bijgewerkt (Stap 3 ✅, volgende = Stap 4: `ep_online_lookup` → `core.ep_online`). **Drie consolidatie-aantekeningen toegevoegd:** (1) PDOK-autosuggest leeft in de browser, niet op de server — `core.bag.vrij_zoeken` via een nieuw server-endpoint is een latere stap; (2) de oude hardcoded BAG-sleutel staat nu verbrand in de git-historie → roteren bij Kadaster + env-var bijwerken urgenter (H8.3); (3) `/api/adres` geeft alleen postcode + huisnummer door (geen huisletter) — startpunt voor frictie #7. Versie 4.19 → 4.20. |
| 4.21 | 6 juni 2026 | **F2 Stap 4 (ep_online) afgerond en gemerged.** De EP-Online-labelstatus achter `/api/ep` vervangen door een dunne adapter (`ep_online_lookup`) rond `core.ep_online.zoek_op_vbo` / `zoek_op_adres` (tegen tag v0.2.0). Oud pad deed rauwe `(status, text)`-passthrough; core geeft geparseerd / `None` / raise. Frontend-contract exact behouden: succes → zelfde JSON-array, geen label (EP 404) → `[]`, input ontbreekt → 400, EP-fout/ontbrekende key → HTTP 200 met foutenvelop (frontend toont "Geen label"). Bewuste keuze: de frontend leunt alleen op de body, niet op de HTTP-status. Hardcoded EP-fallback-sleutel verwijderd — `core.ep_online` eist `EP_ONLINE_KEY` strikt via env-var (staat nu op Railway preview + productie). Contract-pariteitstest `tests/test_ep_pariteit.py`: oud urllib-pad vs nieuw core-pad tegen identieke gemockte EP-responses; 6/6 groen incl. kale omgeving, geen regressie (adres 5/5, prijs 334/334, postcode 6/6). Triviale opschoning: ongebruikte `urllib`-imports verwijderd. Gemerged via PR #6; productie haalt labelstatus nu via de core. H0a bijgewerkt (Stap 4 ✅, volgende = Stap 5: resterende overlap — `ms_graph` → `core.graph_auth`/`graph_api`, agenda-opmaak → `core.agenda_format`, logging → `core.events`). **Consolidatie-aantekeningen bijgewerkt:** verbrande-sleutel-notitie uitgebreid naar BAG + EP (beide te roteren, H8.3), en een nieuwe quirk-notitie (EP-fout → stil "Geen label", behouden; echte foutmelding is latere niet-neutrale verbetering). Versie 4.20 → 4.21. |
| 4.22 | 6 juni 2026 | **F2 Stap 5 (Outlook-opmaak) afgerond en gemerged + architectuur-afspraak.** De lokale opmaak van de opname-afspraak (titel + HTML-body + locatie; `_bouw_event_body` + titelopbouw in `ms_graph.py`) vervangen door `core.agenda_format.opmaak_opname` (tag v0.2.0). Alleen de opmaak — de `ms_graph`-/Graph-aanroepen zelf blijven nog lokaal (latere stap); start/eind-tijd blijft lokaal (UTC→Amsterdam). Eerst vergeleken, geen blinde swap: `tests/test_agenda_opmaak_pariteit.py` legt een bevroren verbatim-kopie van de oude opmaak naast de core op 8 representatieve gevallen — titel, tijd (incl. zomertijd), m²-uit-titel, locatie en body identiek. Twee bewust goedgekeurde afwijkingen, vastgelegd in de test: (1) de overbodige laatste `<br>` onderaan het zakelijk-blok valt weg (core schoner); (2) de core html-escapet alle waarden (veiliger; oude opmaak niet) — met een speciale-tekens-testgeval. Makelaar nog niet doorgegeven (neutraal, leeg). Geen env-var/Railway-actie; geen regressie (ep 6/6, adres 5/5, prijs 334/334, postcode 6/6). Gemerged via PR #7. **Architectuur-afspraak vastgelegd in H4.1:** één Meesterbrein blijft de enige bron van waarheid (geen apart "opmaak"-brein); "opmaak/merk" valt uiteen in (a) de merk-laag in de core (Python: `agenda_format` nu, `email_templates` als volgende consolidatie) en (b) een gedeelde web-UI/design system in de Portal-laag (latere fase, bij de portal-fusie). Aantekeningen bijgewerkt: agenda-format-migratie afgevinkt, makelaar-in-agenda als losse latere feature genoteerd. Versie 4.21 → 4.22. |
| 4.23 | 6 juni 2026 | **F2 Stap 6 (storage) afgerond en gemerged.** De bestand-IO (datamap-detectie + atomic JSON lezen/schrijven) in `storage.py` en `instellingen.py` vervangen door `core.storage` (`vind_data_dir` / `pad_voor` / `laad_json` / `bewaar_json`, tag v0.2.0). Lokaal behouden (nu op core eronder): de afspraken-CRUD en de settings-logica (defaults, diep-merge, validatie); het module-`_lock` blijft om de volledige lees-wijzig-schrijf-cyclus heen (core lockt alleen de schrijf zelf). Bestandsnamen (`afspraken.json` / `instellingen.json`) en atomiciteit gelijk; core checkt dezelfde volume-paden in dezelfde volgorde → op Railway blijft de data op `/app/data/<naam>` staan, zelfde pad, geen migratie. Round-trip-test `tests/test_storage_roundtrip.py` (CRUD + settings naar een tijdelijke datamap): 22/22 groen, geen regressie; geen env-var/secret nodig. Buiten scope: token-persist (`token_persist.json`) in `ms_graph.py` — komt bij de Graph-stap. Gemerged via PR #8. H0a bijgewerkt (Stap 6 ✅, volgende = grote swap `ms_graph` → `core.graph_auth`/`core.graph_api` incl. token-persist). **Notitie (Kevin, 6 juni):** makelaar komt nog steeds niet terug in de agenda-patch — admin-portal geeft `makelaar` nog niet door aan `core.agenda_format.opmaak_opname` (core ondersteunt het al sinds Stap 5); frictie #9 + consolidatie-aantekening bijgewerkt. Versie 4.22 → 4.23. |
| 4.24 | 6 juni 2026 | **F2 afgerond (admin-portal volledig op de core) + nieuwe processectie.** Slotronde A/B/C: **A** — makelaar verschijnt nu in de Outlook-afspraak (frictie #9 opgelost, PR #9); **B** — nieuwe core-module `email_format` (klant- + admin-mailopmaak als pure functies) uitgebracht als **core-tag v0.3.0** (core PR #2), admin-portal-mails lopen nu via `core.email_format`, lokale `email_templates.py` verwijderd (PR #10); **C** — `ms_graph.py` is nu een dunne shim over `core.graph_auth` (token/persist/device-login) + `core.graph_api` (agenda + mail), server.py ongewijzigd (PR #11, handmatig gemerged na MS-env-vars + opnieuw inloggen vanwege de bredere core-scope). Netto: alle gedeelde logica van de admin-portal komt nu uit de core (postcode, prijs, bag, ep_online, agenda-opmaak, bestand-IO, mailopmaak, Graph). H0a + H6a bijgewerkt (F2 ✅, frictie #9 opgelost, frictie #10 wachtwoord-fix toegevoegd). Aantekeningen: bredere Graph-scope (least-privilege als latere core-keuze), secret-rotatie BAG+EP nog open (H8.3), account-note onder H1a (wachtwoord-fix voorbereiden op meerdere accounts). **Nieuwe sectie H5a — Het bedrijfsproces (dossier-levenscyclus):** de ruggengraat met principe 1 (één keer invoeren, overal hergebruiken — K1 als harde regel), principe 2 (flexibele data-gestuurde levenscyclus), de ~13 basisstappen (energielabel), productvarianten (maatwerk-particulier, VvE-maatwerk), de dashboard-weergave en verankering naar H6/H7/H9.5/H6a/events. Versie 4.23 → 4.24. |
| 4.25 | 6 juni 2026 | **Frictie #10 opgelost — wachtwoord wijzigen werkt.** Diagnose: er was geen wijzig-functie; het wachtwoord ís de env-var `ADMIN_PASSWORD` (platte tekst), niet runtime te wijzigen. Fix (PR #12, door Kevin getest + gemerged): nieuwe lokale module `accounts.py` met gehashte wachtwoorden (stdlib pbkdf2-sha256, random salt, 240k iteraties) persistent op de Railway-volume via `core.storage` (`accounts.json`); store = dict gebruiker→hash (multi-account-klaar, vandaag één `admin`). Geen lockout/geen verzonnen wachtwoord: bij lege store wordt eenmalig geseed uit de bestaande `ADMIN_PASSWORD`, daarna is `accounts.json` leidend (env-seed vervalt na een wijziging). `server.py`: login via `accounts.verifieer`, endpoint `POST /api/wachtwoord`, opstart-vereiste versoepeld naar "store óf seed"; UI-sectie op de instellingen-pagina; runtime-data in `.gitignore`. Test `tests/test_accounts.py` (hash round-trip, bootstrap, wijzigen, store-leidend, validatie, geen platte tekst). H6a frictie #10 ✅, H1a account-note bijgewerkt. Volgende stap: secret-rotatie (BAG+EP, H8.3) en de bredere platformfases (F3 e.v.). Versie 4.24 → 4.25. |
| 4.26 | 6 juni 2026 | **F3 gestart — "Dossier voorbereiden" (eerste online-increment) + hernoeming.** De oude "Intake Tool" heet voortaan **"Dossier voorbereiden"** (overal bijgewerkt: H7.2-modulenaam, H10/H10.3, bouwstenen-tabel, H8; historische versiehistorie-regels ongemoeid). Vorm-beslissing (F3.4): **route in de admin-portal** i.p.v. een aparte service. Eerste online-veilige increment gebouwd + gemerged (admin-portal **PR #13**): nieuwe module `voorbereiden.py` (geport uit de leesbron `data_api.py`) levert 3DBAG-gebouwhoogte, voorgevel-oriëntatie (PDOK/OSM + RD-trig, verbatim), woningtype-classificatie en bouwjaar-klasse; route `/voorbereiden` + `GET /api/voorbereiden` halen alles op via core.bag + core.prijs. Additief, geen nieuwe dependency, raakt het aanmeldformulier niet; smoke-test `tests/test_voorbereiden.py` + alle suites groen. **Bewust niet meegenomen (open beslispunten/onbewezen infra):** VABI .epa (lokale templates → F3.5), dossier-output naar OneDrive (F3.3), bewijs-PDF via Playwright, OneNote/To Do. **Upload-spoor afgesplitst** naar een latere fase (richting F6: extern portaal + 2FA + credential + headless browser). H0a/H7.2/H10.3 bijgewerkt; consolidatie-aantekening met de open F3-beslispunten toegevoegd. Versie 4.25 → 4.26. |
| 4.27 | 7 juni 2026 | **F3 "Dossier voorbereiden" online compleet (m.u.v. bewijs-PDF).** Tweede increment (admin-portal **PR #14** + core **PR #3 / tag v0.4.0**): vanaf `/voorbereiden` maakt de knop "Dossier aanmaken in OneDrive" nu een compleet dossier. `vabi_invuller.py` vult het blanco VABI-objectenbibliotheek-sjabloon (geport uit `vabi_generator.py`, leesbron) met de verzamelde velden en levert de `.epa`; `dossier.py` orkestreert OneDrive-map + `.epa` + Invoerkaart.txt (core.graph_api.onedrive), To Do (todo) en optioneel OneNote (onenote). **De cloud rekent niet** (geen nta8800; VABI-berekening blijft handwerk bij Kevin). **Core v0.4.0** levert de VABI-templates als package-data (`energiemeneer_core/objectbibliotheken/` + accessor `objectbib`); de 25MB `EPA_NTA8800.exe` is bewust niet in git (root-map gegitignored). **Multi-user-voorbereiding:** instellingen-blok `dossier` met instelbare afleverlocatie (default = huidige OneDrive-map) + standaard_adviseur + optionele OneNote-config; het dossier draagt een veld 'adviseur' (default = ingelogde gebruiker); Graph-calls nog op `/me`, latere overstap is config. Smoke-tests met gemockte Graph (geen echte schrijfacties); alle suites groen. Resteert in spoor A: bewijs-PDF (Playwright). H0a/H7.2/H10.3 + aantekeningen bijgewerkt. Versie 4.26 → 4.27. |
| 4.28 | 7 juni 2026 | **F3 "Dossier voorbereiden" — onderbouwing hersteld + Job A (automatisch).** (DEEL 1, admin-portal PR #15) `bewijsdocument.py` (geport uit `pdf_generator.py`) zet het onderbouwings-/bewijsdocument weer in het dossier: BAG + 3DBAG-hoogte (ISSO 82.1) + voorgevel-oriëntatie (ISSO 8.3) + PDOK-luchtfoto met voorgevel-pijl — **reportlab + Pillow, géén Playwright** (de Playwright-BAG-viewer-PDF was al vervallen); Invoerkaart.txt verrijkt met SnelStart-velden. (DEEL 2, admin-portal PR #16) `job_voorbereiden.py` — **Job A**: een dagelijkse **in-app scheduler** scant `storage.alle_aankomend()` en bereidt elke opname binnen ~48u automatisch voor (zelfde flow als de knop), **idempotent** (VBO-dedup via `voorbereid.json`), **robuust** per afspraak, met **core.events-logging**; ook handmatig via `POST /api/job-a/run` en `POST /api/dossier/afspraak`. Bron = de afspraak (klant + adres + makelaar al bekend, principe 1). Planning-keuze: in-app scheduler i.p.v. Railway-cron (single-instance service). Instellingen `dossier`: voorbereiden_uren_vooraf (48), dagcyclus_uur (6), dagcyclus_actief. Smoke-tests met gemockte Graph/events (geen echte schrijfacties); alle suites groen. H0a/H5a-stap-4/H6.2-Job-A + aantekeningen bijgewerkt. **Volgende fase:** het dashboard zelf (overzicht openstaande adressen + knop) — de basis (events + handmatige trigger) ligt er. Versie 4.27 → 4.28. |
| 4.29 | 7 juni 2026 | **Dashboard gebouwd (H6, admin-portal PR #17).** `/dashboard` (auth) leest uit `storage` + de voorbereid-registry + `core.events` en toont: **pijplijn** (aankomende opnames + dossier-status voorbereid/niet/mislukt/verschoven, met knoppen "Dossier voorbereiden" en "Job A nu draaien"), **"hangt op"-overzicht** (per dossier, afgeleid van de status of handmatig gezet via `POST /api/dashboard/hangt-op`), **technische gezondheid** (BAG/EP-env + Graph-token, zonder netwerk; recente mislukte events met tijd + oorzaak) en **dossier-detail** (drill-down: gegevens + dossiermap + event-historie). **Re-prep-fix (CC #3):** de voorbereid-registry bewaart nu de afspraak-`start`; een ná voorbereiding verschoven afspraak krijgt status "verschoven" + een "Opnieuw voorbereiden"-knop (`forceer=`). Multi-user-bewust: adviseur-veld meegegeven (`verzamel_dashboard(adviseur=)`), filtering is later config. Datamodel (H9.5) uitgebreid met `dossier_voorbereid`/`hangt_op`/`toegewezen adviseur`; H5a.5 + H6 als gebouwd gemarkeerd. Vrijwel alles lezen; schrijf-acties beperkt tot de bestaande trigger + forceer + hangt-op. Modules `dashboard.py` + `templates/dashboard.html` (bestaande stijl, geen frontend-deps); smoke-test met gemockte storage/job/events/graph. Alle suites groen. Verfijning later: volledige kanban + OneDrive-deeplinks. Versie 4.28 → 4.29. |
| 4.30 | 7 juni 2026 | **Dashboard- en Job A-verfijning + Instellingen-UI (admin-portal PR #18/#19/#20, core tag v0.5.0).** Acht slimmigheden afgerond in de snelle modus (branch → PR → groene Railway-build → auto-merge, lichte smoke-tests met gemockte Graph/events). **Dashboard (PR #18):** OneDrive-**deeplinks** (webUrl van de dossiermap vastgelegd bij aanmaken via nieuwe core-helper `onedrive.web_url`, **core v0.5.0**; klikbaar in dossier-detail), klikbare **filter-tegels + tellingen** (open/voorbereid/mislukt/verschoven), **ververs-knop + lichte auto-refresh** (60s), **alleen-openstaande** fouten in de technische gezondheid (een bron die later alsnog lukte verdwijnt), en een **dagcyclus-samenvatting**-kaart ("X voorbereid, Y mislukt" uit de laatste Job A-run). **Job A (PR #19):** **weekend-slim venster** (vrijdag → t/m eind maandag), **bewijsdocument-luchtfoto-cache** per VBO (opnieuw voorbereiden haalt niet opnieuw op), en een **optionele dagcyclus-samenvattingsmail** naar het bedrijfsadres (standaard uit). **Instellingen-UI (PR #20):** alle dossier-settings als nette velden op `/instellingen` (afleverlocatie, standaard adviseur, To Do-lijst, voorbereiden-uren-vooraf, dagcyclus-draaitijd/actief, samenvattingsmail aan/uit, OneNote notitieboek/sectie/sjabloon) — Kevin bewerkt geen settingsbestand meer; het `dossier`-blok rijdt mee in de bestaande `POST /api/instellingen` (diep-merge vult defaults, validatie ongemoeid). Klant-facing aanmeldformulier niet aangeraakt. Smoke-tests (`test_instellingen.py` nieuw) + alle suites groen. **Uitgesteld:** het volledige kanban-bord (voorbereid → opgenomen → klaar voor upload → geüpload → afgerond) — wacht op latere levenscyclus-stappen die status-events schrijven. H0a/H6/H6.2 + aantekeningen bijgewerkt. Versie 4.29 → 4.30. |
| 4.31 | 7 juni 2026 | **Upload-module geïntroduceerd + increment 1 gebouwd (admin-portal PR #21, core tag v0.6.0).** De **upload-module** (F3, spoor B) handelt een afgerond dossier af in **twee increments**: (1) dossier compleet maken — ontbrekende documenten ophalen; (2) beschikbaar stellen op energielabelkoepel (2FA/browser, increment 2 — nog niet gebouwd, eigen verkenning). **Increment 1 gebouwd:** nieuwe core-functies **`mail.zoek_berichten` + `mail.haal_bijlagen`** (strikt **alleen-lezen**; tag **v0.6.0**, 11 mail-tests, hele core-suite 193 groen). Nieuwe admin-module **`upload.py`** scant de mailbox op afschrift-mails (`noreply_eponline@rvo.nl`, onderwerp "Afschrift energielabel"), parseert `registratienummer_postcode_huisnummer(+toevoeging)` uit de PDF-bijlagenaam en matcht aan een voorbereid dossier op **postcode + huisnummer (+ toevoeging)**; **dubbelzinnig of toevoeging-mismatch → géén match** (precies frictie #7). **Match** → PDF in de OneDrive-dossiermap + dossier-status **"afschrift binnen"** in de **bestaande** dashboard-pijplijn (geen apart blok; nieuwe tegel + badge + afschrift-detail). **Geen match** → map "Ongematchte afschriften" + dashboard-melding via core.events. **Idempotent** via eigen registry `afschriften.json` (op message-id), **robuust** per mail, alles gelogd. **Mailbox wordt nooit gewijzigd** (niets verwijderd/verplaatst/als gelezen gemarkeerd). Trigger `POST /api/upload/afschriften` + automatische stap in de dagcyclus ná Job A. Ondersteunend: voorbereid-registry slaat nu het volledige dossiermappad op; `storage.afspraken_met_lifecycle()` zodat post-opname-dossiers tóch in de pijplijn komen. Smoke-test `test_upload.py` (parse, match incl. frictie #7, end-to-end, idempotentie, robuustheid) + alle suites groen. Klant-facing aanmeldformulier niet aangeraakt. H0a/H5a (stap 8+10)/H7.3 + aantekeningen bijgewerkt. Versie 4.30 → 4.31. |

| 4.32 | 8 juni 2026 | **Drie fixes in "Dossier voorbereiden" + werknamen Job A/B geretired (admin-portal PR #22, core tag v0.7.0).** **FIX 3 (belangrijkste) — overzicht/synchronisatie vond 0 opnames:** oorzaak was dat de dossiervoorbereiding (dashboard + scan) de **lokale `afspraken.json`** las (alléén admin-portal-boekingen) i.p.v. de **live Outlook-agenda**; opnames via het aanmeldformulier/Calendly of handmatig werden zo nooit gezien. Nu leest **alles via de core**: nieuwe core-velden `locatie`+`id` op `agenda.haal_agenda_op` (**v0.7.0**), en een nieuwe admin-module **`agenda_sync.lees_opnames`** haalt de opnames uit de live agenda, herkent ze aan het vaste core-onderwerp ("Energielabel opname") en haalt het adres uit de **locatie**; verrijkt waar mogelijk uit `afspraken.json` (klant/vbo) en — voor het voorbereiden — via `core.bag`. Het dashboard én de synchronisatie gebruiken deze bron; de voorbereid-registry kreeg een `adres_sleutel` zodat een opname zonder vbo_id tóch aan z'n dossier koppelt; detail-drilldown en de handmatige "Voorbereiden"-knop vinden agenda-opnames ook. **FIX 1 — adres-zoekbalk op `/voorbereiden`:** de eigen lookup weggegooid en vervangen door **exact dezelfde universele PDOK-autosuggest** als het aanmeldformulier/`opdracht.html`; lost de toevoeging-bug op (*2512 EX 77 p* → PDOK "Prinsegracht 77P" met "P" als **huisletter**, niet als toevoeging) en laat geen stale resultaten meer staan na een mislukte zoekopdracht. **FIX 2 — "Job A" hernoemd:** knop "Job A nu draaien" → **"Handmatig synchroniseren"**, "Laatste Job A" → **"Laatste synchronisatie"**; in dit document zijn de werknamen **"Job A"/"Job B" geretired** ("automatische dossiervoorbereiding (met handmatige synchronisatie)" resp. "upload-module") — interne endpoint/bestandsnaam blijven; historische versiehistorie-regels ongemoeid. **ONDERZOEK 4 (alleen rapport):** `bewijsdocument.py` is een getrouwe port van `pdf_generator.py` v4.8 — layout, secties, kaart en teksten visueel identiek; verschillen alleen onder de motorkap (bytes i.p.v. bestand, logging, luchtfoto-cache). Eén inhoudelijk punt: de regel **"BAG Nummeraanduiding ID"** is nu leeg (de BAG-adapter levert dat veld niet) — kandidaat voor herstel. Nieuwe smoke-test `test_agenda_sync.py`; `test_dashboard`/`test_job_voorbereiden` omgezet naar de agenda-bron; alle suites groen. Klant-facing aanmeldformulier niet aangeraakt. H0a/H5a/H6/H6.2/H7.2/H7.3/H10 + module-tabel bijgewerkt. Versie 4.31 → 4.32. |

| 4.33 | 8 juni 2026 | **Dashboard-pijplijn met levenscyclus-fases (H5a) + sorteren + twee fixes (admin-portal PR #23).** De pijplijn toont nu per dossier een **fase-kolom** met de stappen uit de dossier-levenscyclus (H5a §5a.3, stap 4–13 — exact overgenomen, bron van waarheid). Nieuwe module `fase.py`: **auto-detectie** van wat we kunnen weten uit de bestaande bronnen (te voorbereiden → stap 4, voorbereid → stap 5 via de voorbereid-registry, afschrift binnen → stap 9 via de afschrift-lifecycle); de overige stappen (opname, VABI, BRL-controle, upload, archiveren, betaling) hebben nog **geen databron** → die zet Kevin **handmatig** een stap verder via een dropdown per dossier, **persistent** via core.storage (`dossier_voortgang.json`, gekoppeld aan de adres-sleutel/token). Voor stappen vóór stap 4 (lead/offerte) is bewust **geen** tracking verzonnen. **Precedentie = `max(auto, handmatig)`:** een auto-mijlpaal duwt de fase alleen vooruit; een handmatig gezette fase wordt nooit stilletjes teruggezet (de dropdown blokkeert opties onder de aangetoonde auto-ondergrens). De kolommen **adres / opname / fase** zijn **client-side sorteerbaar**. **Fix 1 (blanco-adres, 12 jun):** `agenda_sync.parse_locatie` veel robuuster (postcode mag middenin staan, komma optioneel, huisletter mét/zónder spatie, woonplaats optioneel, straatnaam met cijfers); lukt parsen écht niet → de ruwe locatie wordt bewaard en het dashboard toont een nette placeholder i.p.v. een lege regel. **Fix 2 (hangt-op):** wordt nu afgeleid uit de **wacht-op van de huidige fase** i.p.v. een verwarrende vaste tekst (een te-voorbereiden dossier wacht op de *automatische voorbereiding*, niet op Kevin); blijft handmatig bewerkbaar, nu persistent voor álle opnames (ook agenda/Calendly) via de voortgang-store. Nieuwe `test_fase.py`; `test_agenda_sync` uitgebreid (parse-robuustheid + `locatie_raw`); `test_dashboard` omgezet naar het fase-model; alle suites groen. Klant-facing aanmeldformulier niet aangeraakt. H5a.5/H6 bijgewerkt (pijplijn toont nu de levenscyclus-fases, auto + handmatig). Versie 4.32 → 4.33. |

| 4.34 | 8 juni 2026 | **F4 — centrale dossier-datalaag gebouwd (admin-portal PR #24).** Het **dossier** is voortaan de kern-entiteit van de admin-portal (niet meer de agenda), met een **klantregister** eronder — twee persistente stores via core.storage (`klanten.json` + `dossiers.json`). **Klant** (`klanten.py`): voornaam/achternaam, e-mail, telefoon, `factuur_type` (particulier/zakelijk), makelaar, `bedrijf` (naam/adres/**KvK/BTW** = factuuradres) + opmerkingen — exact de velden van het aanmeldformulier (read-only onderzocht), zodat SnelStart later een plug-in is; één klant kan meerdere dossiers hebben (dedup op e-mail, anders naam+telefoon). **Dossier** (`dossiers.py`): `klant_id` + adres, **fase 1–13** (H5a), hangt_op, adviseur, dossiermap/OneDrive-url, gekoppelde agenda-afspraak en mijlpalen (voorbereid/afschrift); primaire sleutel `dossier_id` (een **lead** bestaat al vóór een VBO-ID), met adres-sleutel/VBO/event-id als match-indexen. **Twee manieren van aanmaken:** handmatig via de knop **"Nieuwe klant + dossier"** (kies/maak klant + universele PDOK-adres-zoekbalk + startfase, default lead; `POST /api/dossier/nieuw`) én automatisch via `agenda_sync.synchroniseer_dossiers()` die elke opname op **adres-sleutel/event-id** aan een bestaand dossier koppelt of een nieuw dossier op **fase 4** maakt (**geen dubbelen**; klant gekoppeld waar bekend). **Dashboard:** leest nu de dossier-store (alle dossiers, fases 1–13); de **status wordt uit de fase afgeleid** (mislukt/verschoven/afschrift = vlaggen) — geen tegenstrijdigheid meer; klant zichtbaar per rij; sorteren (adres/klant/opname/fase) + fase-dropdown + precedentie `max(auto, handmatig)` behouden; nieuw **klantregister**-overzicht. De voorbereiding (`job_voorbereiden`) en de afschrift-filer (`upload`) **spiegelen** hun mijlpaal naar het dossier. **Migratie** (eenmalig, idempotent): `dossiers.migreer()` bouwt de store uit `afspraken.json` + `voorbereid.json` + `afschriften.json` + `dossier_voortgang.json` — niets kwijt; de oude registries blijven als idempotentie-cache. **Buiten scope** (niet gebouwd): SnelStart-factuur, auto-instroom aanmeldformulier-leads, koepel-upload increment 2. Klant-facing aanmeldformulier niet aangeraakt. Nieuwe tests `test_klanten`/`test_dossiers`/`test_migratie`; `test_fase`/`test_dashboard` omgezet; alle 20 suites groen. H4.2/H5a.5/H6/H9.5/H10 (F4) bijgewerkt. Versie 4.33 → 4.34. |

| 4.35 | 9 juni 2026 | **Regressie-fix "nieuwe opdracht toevoegen" (BAG-bestendig) + dashboard-sectie "Dossiers in behandeling" (admin-portal PR #25, core tag v0.8.0).** **Diagnose regressie:** het handmatig aanmaken van een opdracht/lead had een **harde afhankelijkheid van een server-side BAG-aanroep** (`/api/adres` → `bag_lookup` → `core.bag.zoek_adres` → `api.bag.kadaster.nl`). Op Railway is die host onbereikbaar geworden — `[Errno 101] Network is unreachable`, een **verbindings-/egress-probleem** (vermoedelijk IPv6/route naar Kadaster), géén logica- of code-fout in `core.bag` (die is ongemoeid) en níét veroorzaakt door PR #24 (die raakte deze flow niet). Het bewezen **agenda-pad** ving BAG-fouten al stil op (`agenda_sync._verrijk_via_bag` try/except), de **manuele** flow niet — daar zat het verschil. **Fix (BAG nooit blokkerend):** `bag_lookup` markeert een verbindingsfout nu als `bag_onbereikbaar`; `/api/dossier/nieuw` maakt het dossier **altijd** aan met klant + (PDOK-)adres en doet de BAG-verrijking **best-effort** (zet `bag_status` = verrijkt/onbereikbaar/niet_gevonden/geen_adres voor een latere retry); de `/opdracht`-pagina degradeert bij `bag_onbereikbaar` naar het PDOK-adres i.p.v. te blokkeren; de knop reset altijd (`finally`). **DEEL 2 — "Dossiers in behandeling":** nieuwe core-functies **`todo.lees_lijsten` / `todo.lees_taken`** (alleen-lezen, tag **v0.8.0**; onbekende lijst → leeg, géén aanmaak) en een read-only dashboard-sectie + route `GET /api/todo` die de openstaande taken uit de Microsoft To Do-lijst 'Energielabels' (instelbaar) toont — defensief: nette lege staat bij geen toegang, geen hang. **Suggestie (niet gebouwd):** de To Do-taken later aan de datalaag-dossiers koppelen door op het adres in de taaktitel te matchen (genormaliseerd, incl. toevoeging — zelfde adres-sleutel als de agenda-sync), zodra de titelvorm bekend is. Tests met gemockte BAG/Graph/To Do (`test_nieuwe_opdracht` + To Do-sectie in `test_dashboard`); alle 21 suites groen. Klant-facing aanmeldformulier niet aangeraakt. H0a-module-6/H6 + consolidatie-aantekening (BAG-onbereikbaarheid) bijgewerkt. Versie 4.34 → 4.35. |
| 4.36 | 9 juni 2026 | **3DBAG-502 bij "Dossier voorbereiden" weerbaar gemaakt (admin-portal PR — `fix/3dbag-502-retry`).** **Diagnose (toen vs nu):** bij het voorbereiden gaf 3DBAG op Railway **HTTP 502** terug → gebouwhoogte faalde, voorgevel-oriëntatie "onbekend", bron "—", en woningtype "Onbekend (fallback)". Onderzoek toont: de 3DBAG-call in `admin-portal/voorbereiden.py` is **byte-voor-byte identiek** aan de bewezen lokale leesbron (`DeEnergieMeneer_IntakeTool/backend/data_api.py`) — zelfde endpoint (`api.3dbag.nl/collections/pand/items/NL.IMBAG.Pand.<id>`), zelfde headers, zelfde timeout — dus **géén code-regressie in hóe 3DBAG wordt aangeroepen** (oorzaak "port roept anders aan" valt af). Een 502 = de 3DBAG-edge is bereikt maar de backend faalde (géén verbindings-/IPv6-probleem, anders dan de BAG-egress van 4.35). Het verschil toen↔nu is de **omgeving**: lokaal een NL-verbinding, nu een Railway-datacenter-IP; 3DBAG (TU Delft onderzoeks-API) geeft onder druk transiënt 502/503. De bewezen code had **geen retry** en stuurde — als enige externe call in die file — **geen echte User-Agent** mee (kale `python-requests`-UA). Eén mislukte `_haal_3dbag_data` cascadeert naar **alle drie** de symptomen (hoogte + oriëntatie + woningtype delen die ene call). **Fix (bewezen parsing blijft verbatim):** nieuwe helper `_3dbag_request` met **retry + backoff** op transiënte 5xx (502/503/504) en netwerkfouten (404 wordt níét geretried), een **echte User-Agent** (`DeEnergieMeneer/1.0 …`, gelijk aan de PDOK/OSM-calls in dezelfde file), en **logging van de exacte request + de 502-body** bij definitieve mislukking zodat op Railway zichtbaar is wát er 502't. Tests met gemockt netwerk (retry-na-502, alle-502-nette-error, User-Agent, geen-retry-op-404); `test_voorbereiden` groen. **Voorbehoud:** blijft het ná retry + echte UA op Railway 502'en, dan is het een **hosting/IP-kwestie** (3DBAG limiteert datacenter-IP's) — geen code-fout; de nieuwe logging maakt dat hard zichtbaar. Klant-facing aanmeldformulier niet aangeraakt. Versie 4.35 → 4.36. |
| 4.37 | 9 juni 2026 | **3DBAG-502 op Railway gediagnosticeerd als 3DBAG-storing + 3DBAG-resultaten persistent gecachet (admin-portal PR #26 retry/logging, PR #27 cache).** Vervolg op 4.36. Met de nieuwe logging kwam de **echte 502-body** binnen: een kale `nginx/1.24.0 (Ubuntu)` 502 Bad Gateway. **Bewijs dat het géén code-/hosting-fout is:** (1) het endpoint is via de **officiële 3DBAG-docs** bevestigd **ongewijzigd** (`https://api.3dbag.nl/collections/pand/items/NL.IMBAG.Pand.<id>`) — oorzaak "endpoint veranderd" valt af; (2) een kale nginx-502 is een **upstream-serverfout**, geen WAF/anti-bot-blokkade (dat zou 403 zijn); (3) de 502 reproduceert **vanaf drie verschillende IP's** — Railway, een ander datacenter-IP én **Kevins eigen lokale NL-browser** — óók op de collectie-root `/collections/pand`. **Conclusie: api.3dbag.nl lag breed plat (server-storing aan TU Delft-kant); herstelt vanzelf.** (De 3DBAG-**viewer** op 3dbag.nl bleef online, maar die draait op aparte tegel-infra en zegt niets over de data-API.) **Robuustheid toegevoegd (PR #27):** 3DBAG is een onderzoeks-API die vaker zal uitvallen, dus elk **succesvol** opgehaald pand wordt nu **persistent gecachet** (`voorbereiden_cache.py` via `core.storage` → `cache_3dbag.json`, atomair, met tijdstempel). Gebouwhoogte, voorgevel-oriëntatie én woningtype blijven daardoor werken voor eerder voorbereide panden, óók tijdens een 3DBAG-502. `voorbereiden.py` blijft zelf **online-veilig** (geen bestand-I/O): de cache wordt **geïnjecteerd** via `stel_3dbag_cache_in()`; `_haal_3dbag_data` schrijft bij succes en valt bij een 502 terug op de cache. **Eerlijke beperking:** de cache redt alleen panden die al eens succesvol zijn opgehaald; een gloednieuw pand voor het eerst opvragen tijdens een storing degradeert nog steeds netjes (geen crash) tot 3DBAG terug is — volledige API-onafhankelijkheid vergt het zelf hosten van de 3DBAG-tegels (grotere, aparte stap). Apart spoor: de **BAG-key** op Railway moet onder de exacte naam `OVERHEID_API_KEY` staan (niet `BAG_API_KEY`) — anders faalt het adres opzoeken. Tests gemockt (retry, cache-fallback); `test_voorbereiden` groen. Klant-facing aanmeldformulier niet aangeraakt. Versie 4.36 → 4.37. |
| 4.38 | 8 september 2026 | **Afwijkend factuuradres: één keten van aanmeldformulier tot factuur (core v0.22.0/v0.22.1 + admin-portal delen 1–5).** Nieuwe core-module **`klant`**: sleutels `factuuradres_afwijkend` + `factuuradres{straat,huisnummer,toevoeging,postcode,plaats}` (exact de formulier-ids `factuur-*` zonder voorvoegsel), `uit_formulier()` (genest of plat), `normaliseer()` (idempotente migratie: een gevuld zakelijk bedrijfsadres → afwijkend=True) en **`factuuradres_van(klant, woonadres)`** als de enige plek waar factuuradres-of-woonadres wordt gekozen, los van het factuurtype. **Portal:** klanten.json draagt de twee sleutels (migratie bij de start via `klanten.migreer_factuuradres_indien_nodig`), de modal 'Nieuwe opdracht' en 'Klant bewerken' hebben dezelfde checkbox + velden (eigen blok 'Factuuradres', zichtbaar bij Particulier én Zakelijk; blok 'Bedrijf' houdt naam/KvK/BTW), de Klant-tegel toont 'Factuuradres (afwijkend)'. **Intake-pad:** website → form-backend `/api/aanvraag/opslaan` → `_naar_intake_contract` → portal `/intake` → `dossiers.upsert_vanuit_intake` → `klanten.vind_of_maak` (sticky, fail-loud met ⚠-logregel + markering in de klant-opmerkingen). **Doorwerking:** SnelStart-robot (aanmaken én bijwerken), invoerkaart en Vabi-Opdrachtgever lezen uitsluitend via `factuuradres_van`. **Bevinding:** het aanmeldformulier stuurt bij "op mijn naam, maar ander adres" de `factuur-*`-velden nog niet mee (alleen `factuur_type`); die formulier-JS moet nog aangepast worden, het portaal accepteert ze al. Versie 4.37 → 4.38. |

*— Einde document —*
