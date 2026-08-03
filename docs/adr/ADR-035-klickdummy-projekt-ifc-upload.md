---
title: "ADR-035: Klickdummy Projekt & IFC-Upload"
status: Accepted
date: 2026-07-14
deciders: Achim Dehnert
scope: cad-hub
conforms_to: platform:ADR-211
tags: [klickdummy]
class: spec-demo
sunset_after: "2027-07-14"
extension_review_required: false
related: []
---

# ADR-035: Klickdummy Projekt & IFC-Upload

## Kontext

`/kd-scout cad-hub`-Lauf (2026-07-14, Klickdummy-Rollout-Queue, Issue
[iilgmbh/iil-klickdummy#176](https://github.com/iilgmbh/iil-klickdummy/issues/176))
fand: cad-hub (nl2cad) ist kein Einzelprodukt-Repo, sondern trägt **3
separate Produktlinien** (`apps/ifc` BIM/NL2CAD-Kern, `apps/avb`
Ausschreibung/Vergabe, `apps/brandschutz` Brandschutz-Prüfung). Dieser KD
deckt bewusst **nur** `apps/ifc` ab — `avb`/`brandschutz` sind eigene,
spätere KD-Kandidaten (Kohärenz-Regel `/kd-scout`).

Innerhalb `apps/ifc` ist Projekt-Anlage + IFC-Upload der Onboarding-Einstieg:
ohne Projekt/Modell ist keine der anderen Journeys (NL2CAD-Abfrage,
Raum-Analyse, Export) nutzbar — Anker-Kandidat.

Erste Adoption von `iil-klickdummy` in diesem Repo (kein vorheriges KD-Setup).
Diese ADR verankert Tooling und Klickdummy in einem Schritt (Empirie
trading-hub PR #139/#143, tax-hub PR #64, dev-hub PR #138, weltenhub PR #42,
dms-hub PR #8, Memory `klickdummy-adoption-needs-ci-gate`).

## Entscheidung

Klasse **`spec-demo`** (nicht `mock`): alle zugrunde liegenden Routen
existieren real und laufen (`apps/ifc/views.py`, `apps/ifc/views_upload.py`).

**Prod-Guard (I2-Externprobe):**
- Query-Parameter `?demo=on` aktiviert den Demo-Render.
- Serverseitiger Flag `KLICKDUMMY_DEMO_ENABLED` (Default `False`) UND
  `settings.DEBUG=True` müssen beide gesetzt sein — `config/settings/production.py:7`
  setzt `DEBUG` bereits hart auf `False`.
- **Noch nicht implementiert** (dieser PR liefert nur Spec + ADR + Tooling,
  keinen Guard-Code in `apps/ifc` selbst). Vor Prod-Wirksamkeit dieses
  Musters ist der Guard nachzuziehen (Folge-Issue, s. Konsequenzen).

3 Screens, aus echtem Code extrahiert (brownfield):

- `projekt-uebersicht` — alle Projekte mit berechneter Modell-Anzahl (`ProjectListView`)
- `projekt-anlegen` — Projekt-Stammdaten-Formular (`ProjectCreateView`)
- `ifc-upload-verarbeitung` — Upload + Status-Pipeline `uploading → processing → ready|error` (`IFCUploadView`, `IFCModel.Status`)

## Konsequenzen

- Tooling-Erstadoption: `.venv-klickdummy` + `make klickdummy-install` neu im
  Repo verankert (bestehendes Makefile um den `klickdummy`-Targetblock
  erweitert).
- CI-Gate (`klickdummy`-Job in `.github/workflows/ci.yml`) im selben PR
  verdrahtet, als eigenständiger Sibling-Job neben `ci`.
- **Folge-Issue nötig:** der `KLICKDUMMY_DEMO_ENABLED`+`?demo=on`-Guard ist in
  diesem PR nur in Spec/ADR deklariert, nicht in `apps/ifc` implementiert.
  Kein I2-Verstoß (Policy: `klickdummy_prod_guard.sh` ist laut
  `~/.claude/policies/klickdummy.md` Rev 20 selbst noch unimplementiert/dormant),
  aber im Repo offen zu tracken.
- Auto-Deploy-on-Merge: `deploy.yml` triggert auf jeden Push nach `main` (kein
  `paths-ignore`) — ein Merge dieses PRs löst einen echten Production-Deploy
  von cad-hub aus (Memory `prod-deploy-preflight-before-merge-approval`).
- **`avb` und `brandschutz` bewusst ausgeklammert** — beides eigenständige
  Produktlinien mit jeweils 15-20 Routen, verdienen einen eigenen
  `/kd-scout`-Lauf statt hier mit hineingequetscht zu werden.

## Bezug

- `platform:ADR-211` — Klickdummy-Konvention
- `apps/ifc/models.py` — `IFCProject`, `IFCModel`
- `apps/ifc/views.py`, `apps/ifc/views_upload.py` — `ProjectListView`/`CreateView`, `IFCUploadView`
- `config/settings/production.py:7` — `DEBUG = False` (Basis des Prod-Guards)
- Issue #176 (iil-klickdummy) — Klickdummy-Rollout-Queue
