# Aanmeldformulier in het dashboard — integratieplan

*Vastgelegd 15 juni 2026. Twee sporen: een korte werkende variant **nu** (Calendly eruit, op info@), en de **toekomst-klare** doel-architectuur voor later. De interim is bewust een opstap naar het doel — geen doodlopende weg.*

---

## 0. In één oogopslag

| | **Nu (Fase A)** | **Later (Fase B)** | **Ambitie (Fase C)** |
|---|---|---|---|
| Doel | Calendly eruit, op info@ | Echte multi-adviseur | Multi-tenant (concullega's) |
| Agenda | één account (info@) | per adviseur, app-rechten | per tenant |
| Opslag | JSON op volume (blijft) | JSON op volume (blijft) | echte database |
| Status | bouwen | team-lichting (met back-ups/rollen) | als (b) speelt |

---

## 1. Fase A — Calendly eruit, nu, op info@ (tijdelijk maar werkend)

**Doel:** het aanmeldformulier boekt niet meer via Calendly, maar levert de lead + afspraak direct aan het dashboard op de bestaande info@-agenda.

**Aanpak — de agenda als bus, maar deterministisch.** Het formulier zet de afspraak in de Outlook-agenda (info@) — zoals nu — maar met een **machine-leesbaar blok** in de event-body in plaats van proza. Het dashboard (`agenda_sync`) herkent de opname en parseert dat blok **deterministisch** → maakt de klant + het dossier op fase 3, met de snapshot gevuld. Geen mailronde, geen fuzzy tekst-parsen.

**Wat er in het blok moet** (afgebakend blok, `sleutel=waarde` of compact JSON):
- Volledig adres **inclusief postcode** → schone `adres_sleutel`, geen dubbele dossiers.
- Product, prijs.
- Woningtype — of expliciet `onbekend`.
- Klant: naam, e-mail, telefoon. Makelaar (optioneel).
- `bron = aanmeldformulier`.

**Woningtype-onbekend → zichtbaar.** "Weet ik niet" mag in het formulier; het systeem doet alsnog een gok uit BAG/3DBAG als *aanname* (`betrouwbaar=False`). Op het bord een **"controleer woningtype"-vlaggetje** zodat de adviseur het verifieert vóór voorbereiden — visueel via StreetView + bovenaanzicht (frictie #5) en vastzetten in de Adresgegevens-kaart.

**Lead-urgentie.** Veroudering op **onafgehandelde** leads (nog geen bevestigde afspraak): groen → oranje → rood naarmate ze ouder worden. Dooft zodra de afspraak bevestigd is (of de lead voorbereiden in gaat). Niet verwarren met klant-**spoed** (+€35, frictie #6) — dat is een ander signaal (klant betaalt voor snel).

**Gratis meegenomen door de fusie:**
- Afspraakbevestiging = opdrachtbevestiging in één (frictie #2/#4) — geen dubbele mail.
- `bron`-veld (self-service / admin / makelaar).

**Expliciet tijdelijk in Fase A:** één account (info@), geen per-adviseur beschikbaarheid. Adviseur blijft een label.

---

## 2. Fase B — toekomst-klaar: multi-adviseur (de keystone)

**De steen:** "adviseur" wordt een **eerste-klas identiteit**, niet één Kevin-token.
- Elke adviseur = { Microsoft-e-mail/UPN, eigen werktijden, rol, actief }.
- Eén app-registratie met **scoped Graph-rechten**; de agenda is geparametriseerd op de adviseur i.p.v. hardcoded `/me`.

**Wat erop volgt (alles parametrisering):**
- Beschikbaarheid = agenda + werktijden van adviseur X.
- Boeken = opname in de agenda van X.
- `agenda_sync` loopt over **álle** actieve adviseurs.
- Toewijzen/herverdelen = event verplaatsen + dossierlabel + herberekenen (een echte handeling, geen labelflip).

**De product-winst:** formulier (en admin) tonen **gecombineerde beschikbaarheid** en wijzen automatisch een vrije adviseur toe → "info@ vol, nieuweadviseur@ vrij" lost zichzelf op, en de agenda is als geheel voller boekbaar.

**Rol-gebaseerde toegang:** elke adviseur logt in, ziet/doet wat z'n rol toestaat (`accounts.py` is hierop voorbereid).

**Keystone-keuze (bewust kiezen):**

| Optie | Voor | Tegen |
|---|---|---|
| **App-rechten** (advies) | clean, geen per-adviseur-inlog, multi-tenant-klaar | krachtig secret → strak scopen (`Calendars.ReadWrite` + `Mail.Send`) + goed beschermen |
| Delegated per adviseur | conservatief, geen almachtig secret | meer losse onderdelen (N refresh-tokens) |

**Hoort in de "klaar-voor-een-team"-lichting** samen met back-ups, rol-rechten en concurrency-hardening — want meerdere adviseurs die tegelijk schrijven maken het lost-update-risico reëel.

---

## 3. Fase C — ambitie: multi-tenant (concullega's)

- Echte database met **per-tenant scheiding** (JSON-op-volume isoleert tenants niet).
- Multi-instance hosting.
- Pricing/billing als eigen module.

**Belangrijk:** de identiteits-/adviseurlaag uit Fase B is exact wat dit nodig heeft → je bouwt 'm één keer. De database/hosting is een aparte latere sprong erbovenop, geen overdoen.

---

## 4. De brug — hoe Fase A de toekomst niet dichttimmert

**Bewust multi-ready gemaakt in Fase A** (kost nu bijna niks):
- Het **gestructureerde agenda-blok** blijft het transport — ook in Fase B.
- Het adviseur-veld krijgt nu al plek voor een **Microsoft-e-mail** (vandaag alleen Kevin gevuld).
- Agenda-rakende code wordt **adviseur-geparametriseerd** met default = Kevin, i.p.v. hardcoded `/me`.

**Expliciet tijdelijk** (wordt in Fase B vervangen): de single info@-agenda, geen per-adviseur beschikbaarheid, adviseur-als-label.

---

## 5. Volgorde

1. **Fase A — nu:** Calendly eruit, agenda-bus op info@, gestructureerd blok, woningtype-vlag, lead-urgentie.
2. **Fase B — in de team-lichting:** adviseur-identiteit + app-rechten → per-adviseur agenda/sync/mail → formulier met gecombineerde beschikbaarheid.
3. **Fase C — als (b) echt speelt:** database + multi-tenant + hosting.

---

*Principe (uit Meesterbrein): waar een keuze tussen "single-user simpel" en "multi-user-klaar" weinig extra kost, kiezen we bewust de laatste — bouw geen deuren dicht. Fase A levert vandaag waarde op info@; Fase B legt de steen die alles toekomst-klaar maakt; Fase C is de SaaS-sprong erbovenop.*
