# ONBOARDING.md — voor nieuwe ontwikkelaars op het EnergieMeneer-platform

> Dit document is geschreven voor een ervaren software engineer / UI-UX designer
> die nieuw is op dit project. Het doel: binnen 30 minuten weten wat dit project
> is, hoe het in elkaar zit en in welke werkwijze je inhaakt — zonder Kevin met
> basisvragen te belasten.
>
> Lees dit document samen met `CLAUDE.md`. Verschil: `CLAUDE.md` is afgestemd op
> Kevin (niet-programmeur) en beschrijft de afspraken voor zíjn Claude
> Code-sessies — beschouw dat als **achtergrond**. Deze `ONBOARDING.md` is
> **voor jou specifiek**. De inhoudelijke conventies (codestijl, strangler,
> PR-flow) gelden voor iedereen.

---

## 1. Wat is dit project

Eigenaar is **Kevin Valkenhoff** (De EnergieMeneer, energielabel- en
VvE-consultancy in Den Haag). Het bedrijf draait vandaag op **vijf losse tools**
die elk hun eigen kopie bevatten van dezelfde logica (Microsoft Graph-auth,
BAG-lookup, EP-Online, prijsmatrix, Outlook-agenda-format, pad-detectie):

- **Aanmeldformulier** — klant-self-service intake (Railway)
- **Admin Portal** — handmatige intake door Kevin (Railway)
- **Intake Tool** — dossiervoorbereiding (lokaal, Flask)
- **Uploadtool** — upload naar EnergielabelPortaal (lokaal, Tkinter + Playwright)
- **VvE-tool** — adressenoverzicht per VvE (los CLI-script)

Het doel is die vijf tools te consolideren tot **één online platform** bovenop
een gedeelde Python-library: `energiemeneer-core`. De gedupliceerde logica gaat
naar één bron van waarheid; elke tool importeert die voortaan in plaats van te
kopiëren. Dat maakt elke volgende uitbreiding (dashboard, automatisering,
VvE/advies) goedkoper en minder bug-gevoelig.

**Stack:** Python (Flask + rauwe `http.server`), Railway (hosting + PR-previews),
OneDrive, Microsoft Graph API, GitHub.

Voor de strategische diepte — visie, knelpunten, architectuur in lagen, datamodel,
contracten en de volledige roadmap — zie **`Meesterbrein.md`**. Dat is het
leidende document; dit is de praktische instap.

---

## 2. Repositories

| Repo | Rol |
| --- | --- |
| **De-Energiemeneer/energiemeneer-core** | De gedeelde library (hier staat deze ONBOARDING.md). Modules 1–10 af (o.a. klant, product, agenda_format), 292 tests groen, laatste tag v0.24.0 (10-9-2026). |
| **De-Energiemeneer/admin-portal** | Eerste tool die wordt gemigreerd. Draait live op Railway, neemt de core al als dependency. |
| **De-Energiemeneer/energiemeneer-aanmeldformulier** | Tweede tool, nog te migreren. |

Je krijgt **collaborator-toegang** van Kevin op de relevante repos. Zonder die
toegang kun je niet pushen of PR's openen — vraag erom als je clone-/push-fouten
krijgt.

---

## 3. Hoe het project georganiseerd is

Drie documenten vormen samen de spelregels:

- **`Meesterbrein.md`** — het strategische document en de **één bron van
  waarheid**. Bevat visie, architectuur, contracten (prijzen, scopes,
  agenda-format, datamodel) en de roadmap. Versiebeheer leeft in het document
  zelf (versietabel bovenin + versiehistorie onderaan). **Alleen Kevin werkt dit
  bij**, tenzij expliciet anders afgesproken. Wijzig dit niet op eigen houtje.
- **`BOUWPLAN.md`** — de module-volgorde en het bouwritme van de core. Beschrijft
  de strangler-discipline op modulenivo.
- **`CLAUDE.md`** — de werkafspraken voor Kevins Claude Code-sessies. Achtergrond
  voor jou: het verklaart de toon en de conventies, maar is op Kevin afgestemd.
- **`ONBOARDING.md`** (dit document) — jouw specifieke instap.

Vuistregel: een vraag over *waarom* iets zo is → `Meesterbrein.md`. Een vraag
over *hoe* de core gebouwd wordt → `BOUWPLAN.md`. Een vraag over *hoe je inhaakt*
→ dit document.

Naast de documenten bestaat er een **samenwerkingsdriehoek**: **Claude in de
chat** (strateeg/gids — bewaart de Meesterbrein-context en maakt plannen),
**Claude Code** (de developer in de terminal — voert uit, test, pusht en denkt
actief mee) en **Kevin** (eigenaar/beslisser — eindregie, review en merge).

Waar val jij in? Je bent — net als Claude Code — een **developer met eigen
inzicht**: je voert uit, reviewt, en je mag (graag zelfs) beargumenteerd
betere routes voorstellen, met Kevin als eigenaar/beslisser. De chat-Claude is
vooral Kevins strategische sparringpartner; jij hoeft daar niet doorheen te
werken voor concreet ontwikkelwerk. De volledige rolverdeling staat in
**Meesterbrein H0b — Werkwijze**.

---

## 4. De strangler-migratie (huidige fase F2)

Het platform wordt niet in één keer herbouwd. De aanpak is **strangler**: een
tool blijft draaien, en je vervangt hem **functie voor functie** door een
aanroep naar de core. Pas als de vervanging bewezen werkt, verwijder je de
lokale duplicaat. **Nooit big-bang**, nooit een werkende kopie slopen voordat de
vervanger groen is.

Het patroon is vastgelegd in **Meesterbrein H10.2 → F2.2**. Kernpunten:

- **Splits elke migratie in 1a en 1b.**
  - *Stap 1a (plumbing):* core als dependency toevoegen + test toevoegen,
    **géén gedragsverandering**. Eigen branch, PR, preview-build. Bewijst dat de
    leiding werkt voordat er functionaliteit verschuift.
  - *Stap 1b (gedrag):* nú pas de lokale functie vervangen door de core-aanroep
    en de duplicaat verwijderen. Niet mengen met 1a in dezelfde commit-historie.
- **"Bevroren ijkpunt"-test.** In de tool-test staat een ingebakken kopie van de
  *oude* lokale logica/uitkomst. Ook nadat de echte lokale code weg is, blijft
  die test bewaken dat de core exact hetzelfde doet als wat de tool vroeger deed.
  Zo vang je een stille gedragsafwijking direct.

**Canoniek voorbeeld:** PR #1 op `De-Energiemeneer/admin-portal` — de
postcode-normalisatie (`normaliseer_postcode`) werd vervangen door
`core.bag.normaliseer_postcode`. Lees die PR end-to-end; het is het referentie-
patroon voor elke volgende stap.

---

## 5. De PR-workflow (verplicht voor élke wijziging)

**Er gaat nooit een directe push naar `main`/`master`.** Zonder uitzondering.
Werkwijze (vastgelegd in **Meesterbrein H10.2 → F2.1**):

1. Branch maken in je werkkopie.
2. Pushen naar GitHub.
3. Pull Request openen (base: `main`, compare: je branch).
4. Railway maakt **automatisch een PR-environment** aan (`<service>-pr-N`) en
   draait daar build + healthcheck — productie wordt niet aangeraakt.
5. **Functionele test op de preview-URL** van die PR-environment.
6. Pas na groen vinkje + bewezen werkend: **Kevin** merget naar main (zie §7) →
   Railway deployt naar productie. PR sluiten → environment wordt opgeruimd.

> Let op: Railway's *Focused PR Environments* is bewust uitgezet (markeerde een
> service ten onrechte als "niet geraakt"). Met één service per project werkt de
> standaard PR-environment prima.

**Branch-naamconventie** (voorstel, definitief vast te leggen in §"Belangrijke
afspraken"):

- `feature/<korte-omschrijving>` — nieuwe functionaliteit
- `fix/<korte-omschrijving>` — bugfix
- `migratie/<functie>` — een strangler-stap die logica naar de core trekt

---

## 6. Setup voor je computer

- **OS:** Windows + WSL/Ubuntu (zelfde stack als Kevin) **óf** native macOS/Linux.
  De command-line is identiek; kies wat je prettig vindt.
- **Git** geconfigureerd met je eigen naam + je GitHub-e-mail.
- **Claude Code** geïnstalleerd op je eigen Anthropic-abonnement (optioneel maar
  aanbevolen — Kevin werkt er volledig mee).
- **VS Code** aanbevolen, niet verplicht.

Repos clonen:

```bash
git clone git@github.com:De-Energiemeneer/energiemeneer-core.git
git clone git@github.com:De-Energiemeneer/admin-portal.git
git clone git@github.com:De-Energiemeneer/energiemeneer-aanmeldformulier.git
```

Eerste keer dependencies installeren (per repo):

```bash
cd admin-portal && pip install -r requirements.txt
```

De core kun je lokaal installeren en testen:

```bash
cd energiemeneer-core && pip install -e . && pytest
```

> **Lokaal volledig draaien lukt NIET zonder Microsoft Graph-tokens.** Die zijn
> van Kevins persoonlijke account en worden niet gedeeld of gedupliceerd (zie §8).
> Voor functionele tests is de **Railway PR-preview** de norm, niet je localhost.

---

## 7. Wat je kunt en NIET kunt zonder Kevin

**Zelfstandig (geen Kevin nodig):**

- Code lezen, doorgronden, reviewen.
- Branches maken en pushen.
- PR's openen.
- Tests draaien — lokaal op de core en functioneel op de PR-preview.
- Ontwerpen/oplossingen voorstellen (jouw UI/UX-blik is hier expliciet welkom).
- Meedenken in Meesterbrein-vraagstukken via chat/overleg.

**Niet zonder Kevin (zijn eindbeslissing):**

- **Mergen naar main** — de eindbeslissing en de merge zijn van Kevin.
- **Productie-environment-variabelen** wijzigen in Railway.
- **Microsoft-credentials** (Azure-app, tokens) wijzigen.
- **Strategische roadmap-wijzigingen** — die leven in Meesterbrein en zijn van
  Kevin.

> Bij twijfel: vraag het. **Blokkeer niets**, sloop geen werkende code, en forceer
> geen merge. Een open vraag is goedkoper dan een teruggedraaide productie-deploy.

---

## 8. Speciale aandachtspunten over dit project

- **Microsoft Graph-tokens** horen bij Kevins persoonlijke account en zijn niet
  lokaal te delen of te dupliceren. Daarom test je functioneel op de **Railway
  PR-preview**, niet op localhost.
- **Secrets staan als env-vars in Railway — NOOIT in code.** De Docker-build geeft
  waarschuwingen over secrets via ARG/ENV; dat is **bekende, geaccepteerde schuld**
  die samen met de secret-rotatie wordt opgeruimd (zie Meesterbrein **H8.3**).
- **Bedrijfsgegevens** (adres, KvK, BTW, e-mail, telefoon) worden via
  `/instellingen` op de live app gezet — **niet** als code-defaults. Code-defaults
  blijven leeg of bevatten alleen veilige fallbacks.
- **Code-conventies** (gelden voor iedereen):
  - **Nederlandse functienamen** (bijv. `vind_data_dir`, `zoek_adres`,
    `bereken_prijs`).
  - **Nederlandse, begrijpelijke foutmeldingen.**
  - Logging via `logging.getLogger("energiemeneer_core.<module>")` — **nooit
    `print`**.
  - **Atomic writes** voor bestanden (tmp + `os.replace`), met lock waar nodig.
  - **Tests met pytest**; externe calls (HTTP) altijd mocken — geen echte
    netwerkcalls in tests.
  - **Geen hardcoded API-keys of secrets**, ook niet als fallback. Ontbreekt een
    key → nette `RuntimeError` die vertelt welke env-var gezet moet worden.

---

## 9. Eerste week — voorgestelde rondleiding

- **Dag 1 — Lezen.** `Meesterbrein.md` (vooral H0a Bouwstatus, H1 Visie, H7
  Modules, H10 Roadmap), `BOUWPLAN.md`, `CLAUDE.md` en deze `ONBOARDING.md`.
- **Dag 2 — Opzetten.** Clone beide tool-repos + de core. Draai de core-tests
  lokaal (`pytest`). Lees `server.py` van de admin-portal end-to-end.
- **Dag 3 — Het canonieke voorbeeld.** Lees **PR #1** op `De-Energiemeneer/admin-portal`
  volledig door (postcode-normalisatie). Dit is hét referentievoorbeeld van een
  strangler-stap: 1a/1b, bevroren-ijkpunt-test, preview-flow.
- **Dag 4 — Eerste kleine taak.** Suggestie: de **testknop op `/instellingen`**
  (admin-notificatie sturen zónder een afspraak in te plannen — staat als
  aandachtspunt in Meesterbrein H0a). Eigen branch → PR → preview → review met
  Kevin. Geïsoleerd, geen strangler — ideaal om de workflow te leren.
- **Dag 5+ — Inhaken op de migratie.** Pas hierna pak je echte strangler-stappen
  aan de core op.

---

## 10. Wat als je vastloopt?

1. **Zoek eerst in `Meesterbrein.md`** — de meeste "waarom"-vragen staan daar.
2. **Dan `BOUWPLAN.md` en `CLAUDE.md`** — voor bouwritme en conventies.
3. **Dan Kevin** — stuur een Slack/Teams-bericht mét context: wat je probeert,
   wat je verwachtte, wat er gebeurt.
4. **Urgente blokker** (productie ligt plat): **bel Kevin direct.**

---

## Belangrijke afspraken om toe te voegen

> Ruimte voor afspraken die uit de praktijk naar boven komen. Kevin en de collega
> vullen dit samen aan (branch-conventie definitief vastleggen, codereview-
> praktijk, definition-of-done, communicatiekanaal, enz.).

-
