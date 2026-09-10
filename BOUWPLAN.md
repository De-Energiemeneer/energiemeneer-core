# BOUWPLAN — energiemeneer-core

> Dit bestand is de leidraad voor het bouwen van de gedeelde core-library.
> Lees dit volledig voordat je begint. Werk strikt in de aangegeven volgorde.
> Geschreven samen met Claude (chat) op basis van het Meesterbrein v4.0.

---

## 1. Waarom deze library bestaat

Kevin (De EnergieMeneer) heeft vijf losse tools die elk hun eigen kopie
bevatten van dezelfde logica: Microsoft Graph-auth, BAG-lookup, EP-Online,
prijsmatrix, Outlook-agenda-format en volume-pad-detectie. Bewezen duplicatie:
de functie `_find_data_dir` staat identiek in DRIE bestanden; `maak_todo_taak`
en de hele auth-laag staan dubbel.

`energiemeneer-core` wordt de ENIGE bron van waarheid voor die gedeelde logica.
Elke tool gaat straks importeren uit deze library in plaats van te kopiëren.

Doel voor Kevin: elke wijziging (een tarief, een scope, het agenda-format)
hoeft straks nog maar OP ÉÉN PLEK. Dat scheelt onderhoud en bugs, en maakt
alles wat erna komt (fusie van tools, dashboard, automatisering) goedkoper.

---

## 2. De gouden regel: strangler-aanpak (NOOIT big-bang)

Bouw module voor module. Per module dit ritme, in deze volgorde:

1. Schrijf de module in `energiemeneer_core/` op basis van de SCHOONSTE
   bestaande versie uit een van Kevins tools (niet vanaf nul verzinnen —
   hergebruik bewezen code).
2. Schrijf een kleine test die bewijst dat de module doet wat hij moet doen.
3. Commit.
4. PAS LATER (in een aparte stap, bij de tools zelf): vervang in één tool de
   lokale kopie door een import uit de core. Draai die tool. Bevestig dat de
   output identiek blijft. Verwijder dan pas de oude kopie.

NOOIT een werkende kopie slopen vóórdat de vervanging bewezen werkt.

---

## 3. Volgorde van modules (van veiligst naar gevoeligst)

Bouw in DEZE volgorde. Niet vooruitlopen.

### Module 1 — `storage`  (EERST, laagste risico)
- Volume-/datamap-detectie + atomic JSON lezen/schrijven.
- Bron: de schoonste versie staat in de Admin Portal `storage.py`
  (heeft al atomic write via tmp-bestand + os.replace).
- Vervangt straks: `_find_data_dir` (3 kopieën) + store-lezen/schrijven.
- Dit is de oefenmodule om het patroon te leren. Houd het simpel.

### Module 2 — `bag`
- Adres- en pandgegevens via BAG + PDOK Locatieserver.
- Bron: identiek in meerdere tools; pak één en maak generiek.
- API-key via environment variable (NIET hardcoden).

### Module 3 — `ep_online`
- Energielabel-status via EP-Online v5.
- API-key via environment variable.

### Module 4 — `prijs`
- De prijsmatrix (zie Meesterbrein H9.1). Pure functie: oppervlakte +
  nieuwbouwvlag → categorie + bedrag. Geen externe calls.

### Module 5 — `graph_auth`  (GEVOELIGST — pas hier als patroon zit)
- Microsoft-token ophalen, verversen, persistent bewaren.
- Bron: het Aanmeldformulier `ms_graph.py` is het volledigst (heeft
  token_persist.json + refresh-logica).
- Dit lost Kevins terugkerende token-pijn structureel op.

### Module 6 — `graph_api`
- Agenda, To Do, Mail, OneDrive, OneNote via Graph. Bovenop graph_auth.

### Module 7 — `agenda_format`
- De vaste Outlook titel/body-opmaak (zie Meesterbrein H9.3). Het "merk".
  Eén bron, identiek voor alle instroomkanalen.

### Module 8 — `events`  (toegevoegd na F1, vóór F2)
- Centrale append-only logging: elke module schrijft wat hij deed
  (wie/wat/wanneer/resultaat). Fundament voor het dashboard (zie
  Meesterbrein H4.2 + H6). Bovenop `storage`.
- Strikte waarden: `resultaat` ∈ {gelukt, mislukt, in_uitvoering},
  `niveau` ∈ {info, waarschuwing, kritiek}. Opslag als JSON Lines, achter
  één interne functie zodat later een echte DB (B1) kan komen.

---

## 4. Vaste afspraken (contracten)

Deze waarden komen uit het Meesterbrein v4.0 H9 en zijn leidend.

**Prijsmatrix (incl. BTW):**
- Tot 100 m²: bestaand €280 / nieuwbouw €425
- 100–150 m²: €315 / €460
- 150–200 m²: €355 / €500
- >200 m² of onbekend: maatwerk
- Spoedtoeslag: +€30

**Microsoft Graph scopes:**
Files.ReadWrite, Tasks.ReadWrite, Notes.ReadWrite, Calendars.ReadWrite,
Mail.Send, offline_access

**Outlook-afspraak format:**
- Titel: Energielabel opname — [Straatnaam huisnr], [Woonplaats]
- Locatie: volledig adres. Duur: 90 min. Reminder: 60 min vooraf.
- Body: klantnaam, e-mail, telefoon, adres, woningtype, prijs, huidig
  label, makelaar (indien ingevuld), zakelijke gegevens, opmerkingen.

---

## 5. Belangrijke randvoorwaarden

- **GEEN secrets in de code.** Alle API-keys en de Microsoft client-secret
  via environment variables. Als je hardcoded keys tegenkomt in Kevins oude
  code: NIET overnemen, vervangen door os.environ. (Oude secrets moeten t.z.t.
  geroteerd worden — noteer dit, maar dat is een aparte actie.)
- **Communiceer in het Nederlands**, informeel maar professioneel.
- **Leg in gewone taal uit** wat je doet voordat je het uitvoert. Kevin is
  geen doorgewinterde programmeur; wees een geduldige gids.
- Bij twijfel over de schoonste bronversie van een functie: vraag het,
  raad niet.

---

## 6. Hoe te beginnen (volgende sessie)

Zeg tegen Claude Code:
"Lees BOUWPLAN.md. We beginnen met Module 1 (storage). Leg eerst uit hoe je
het aanpakt voordat je code schrijft."

Werk dan stap voor stap. Eén module per keer. Test en commit na elke module.
Push naar GitHub als een module af en getest is.

---

## 7. Status bijhouden

Vink af wat klaar is (laat Claude Code dit updaten):

- [x] Module 1 — storage  *(commit 5b3dd68, 9/9 tests groen)*
- [x] Module 2 — bag  *(12/12 tests groen; zoek_adres + vrij_zoeken + normaliseer_postcode)*
- [x] Module 3 — ep_online  *(10/10 tests groen; zoek_op_vbo + zoek_op_adres)*
- [x] Module 4 — prijs  *(31/31 tests groen; bereken_prijs incl. spoedtoeslag en maatwerk)*
- [x] Module 5 — graph_auth  *(13/13 tests groen; public client, refresh-rotatie in token_persist.json, ntfy-noodmelding met 24u-rem)*
- [ ] Module 6 — graph_api  *(in onderdelen)*
  - [x] 1. agenda  *(15/15 tests groen; generieke CRUD + gedeeld _client-loket met 401-herstel)*
  - [x] 2. mail  *(6/6 tests groen; generieke stuur_mail met cc/bcc/reply-to, één adres of lijst)*
  - [x] 3. onedrive  *(11/11 tests groen; generieke maak_map met _1/_2-logica + upload_bestand met grote-bestand-sessie >4MB)*
  - [x] 4. todo  *(7/7 tests groen; generieke maak_taak met lijst zoeken/aanmaken + _1/_2-logica + optionele deadline)*
  - [x] 5. onenote  *(12/12 tests groen; generieke kopieer_sjabloonpagina — notitieboek/sectie/sjabloon als parameters, async copyToSection met operatie-polling i.p.v. blinde sleep, expliciete lege-pagina-terugval i.p.v. stille fallback)*
- [x] Module 7 — agenda_format  *(17/17 tests groen; pure opmaak losgekoppeld van de agenda-laag: opmaak_opname → titel (klant + m² + Amsterdamse tijden) + HTML-body (klant/adres/makelaar/zakelijk/opmerking, HTML-veilig) + locatie + herinnering; bereken_eindtijd voor de vaste 90 min)*
- [x] Module 7b — agenda_format B1 (v0.24.0, 10-9-2026)  *(titel per product via `product.agenda_titel`, markering `[Energiemeneer-afspraak: <product>]` in de body, `is_opname`/`product_uit_body`; zonder product byte-gelijk)*
- [x] Module 9 — klant  *(factuuradres v0.22 + VvE-blok B1 v0.24.0: `schoon_vve`, `vve_uit_formulier`, `vve_ontbrekende_velden`, beheerder-helpers; tests/test_klant.py)*
- [x] Module 10 — product  *(v0.23.0 catalogus met profiel per product; B1 v0.24.0: `ob_automatisch`, `woning_eisen`, `agenda_titel`, profiel Energiescan VvE bijgesteld)*
- [x] Module 8 — events  *(16/16 tests groen; append-only JSONL-logboek bovenop storage. schrijf_event + lees_events met filters (module/vbo_id/resultaat/niveau/sinds/limiet), nieuwste eerst. Strikte resultaat- en niveau-waarden met ValueError; corrupte regels overgeslagen)*
