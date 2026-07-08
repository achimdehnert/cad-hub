# cad-hub — Agent Handover Document

> **ADR-086-konform** | Zuletzt aktualisiert: 2026-03-03 | Review-Intervall: 30 Tage

> _Anker-Block unten ist generiert (`platform/tools/agent-handover`); Re-Runs ersetzen nur den Block zwischen den Markern. Restliches Dokument von Hand gepflegt._

<!-- AGENT_HANDOVER:AUTO START — generiert via platform/tools/agent-handover, nicht von Hand editieren -->
## Aktueller Stand
| Attribut | Wert |
|---|---|
| Zuletzt aktualisiert | 2026-05-29 |
| Branch | main |
| Phase | _siehe `project-facts.md` / vom Bearbeiter pflegen_ |

## Verifizierbare Anker
> **Empfänger-Ritual:** Diese Anker ZUERST prüfen, bevor du dem Prosa-Stand glaubst.
> Stimmt einer nicht → Handover als veraltet behandeln.
| Anker | Wert | Prüfbefehl |
|---|---|---|
| Letzter stabiler SHA | `d232007 chore(workflows): sync session-ende.md from platform` | `git log --oneline -1 d232007` |
| CI-Status | failure@26641452312 | `gh run list -L1 --branch main` |
| Migrationen | siehe Prüfbefehl (DB nötig) | `python manage.py showmigrations | grep '\[ \]'` |
| Working-Tree sauber | n/a (Snapshot von origin/main) | `git status --porcelain` |

## SSoT-Zeiger (referenzieren, NICHT nacherzählen)
- Projekt-Fakten: `project-facts.md`
- Relevante ADRs: `cad-hub:ADR-029`, `cad-hub:ADR-034`
- Orchestrator-Memory: `agent_memory_search "cad-hub"`

## Was wurde zuletzt getan?
- 2026-05-29 chore(workflows): sync session-ende.md from platform
- 2026-05-29 chore(workflows): sync new-github-project.md from platform
- 2026-05-29 chore(workflows): sync onboard-repo.md from platform
- 2026-05-29 chore(workflows): sync drift-check.md from platform
- 2026-05-28 chore(workflows): sync run-local.md from platform
<!-- AGENT_HANDOVER:AUTO END -->

## Repo-Zweck

`cad-hub` ist eine **Django-Plattform für CAD-Daten-Verarbeitung** (BIM/IFC/DXF).
Nutzt `nl2cad-*` Packages als Downstream-Konsument.

---

## Technischer Stack

| Komponente | Details |
|------------|---------|
| Framework | Django 5.x |
| Python | >= 3.11 |
| Frontend | HTMX + Tailwind CSS |
| DB | PostgreSQL 16 (django_tenancy) |
| CAD | nl2cad-core, nl2cad-areas, nl2cad-gaeb |
| Container | Docker Compose (`docker-compose.prod.yml`) |
| Registry | GHCR (`ghcr.io/achimdehnert/cad-hub/`) |

---

## Kritische Regeln

- **Service-Layer**: `views.py` → `services.py` → `models.py`
- **Multi-Tenancy**: `django_tenancy` — alle Queries tenant-isoliert
- **nl2cad**: CAD-Logik in nl2cad-Packages, NICHT in Django-Views
- **HTMX**: kein custom JS
- **Templates**: alle erweitern `base.html`
- **Migrations**: nie automatisch

---

## Verbotene Pfade (ADR-081)

```
migrations/, .env*, config/settings/prod*, *.pem, *.key, docker-compose.prod.yml
```

---

## Deployment

```bash
docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/cad-hub/cad-hub-web:latest .
docker push ghcr.io/achimdehnert/cad-hub/cad-hub-web:latest
```

Server: `88.198.191.108` | Workflow: `/deploy`

---

## Workflows (Windsurf)

| Workflow | Zweck |
|----------|-------|
| `/agent-task` | Task ausführen (ADR-086) |
| `/deploy` | Deployment |

---

## ⚡ Aktueller Stand (Session 2026-07-08, Achim + Claude Code)

**Erledigt** (Teil der Statusanalyse nl2cad+cad-hub, ADR-011/ADR-012 in nl2cad):
- PR #31 gemergt: `nl2cad-core[ifc]>=0.4.0` gepinnt, toter `apps/ifc/parser/parser.py` (`IfcCompleteParser`) entfernt.
- PR #33 gemergt: `requirements.txt` entschlackt — `nl2cad-nlp` + `iil-nl2cadfw` entfernt (beide verifiziert 0 Imports).
- PR #34 gemergt: totes Duplikat `apps/ifc/services/cad_loader.py` entfernt (kaputte relative Imports, nie aktiv referenziert).
- Deploy nach diesen Merges verifiziert **erfolgreich** (nicht nur CI grün) — Run-ID 28927144407, `conclusion: success`.

**Läuft — ADR-012-Migration (nl2cad↔cad-hub DXF-Boundary), pausiert:**

Ziel: `apps/dxf`/`apps/ifc` sollen für Parsen/Analyse `nl2cad.core` konsumieren statt eigenen `ezdxf`-Code zu halten (ADR-012 im nl2cad-Repo, akzeptiert). Gap-Analyse (2026-07-08) ergab:

- `DXFParserService.extract_room_candidates` (`apps/dxf/services/analyzer/dxf_parser.py:542`) — der ursprünglich als "Stufe 1" geplante Austausch — hängt an `DXFParseView`/`/dxf/parse/`, das **keine Frontend-Vorlage aufruft** (verifiziert: 0 Treffer in `templates/`/JS). Kein Nutzerpfad, kein sichtbarer Gewinn.
- Der **reale** Nutzerpfad (Grundriss-Tab in `analysis.html`) läuft über `DXFAnalyzeUploadView` → `CADLoaderService.get_rooms()`/`get_room_areas()` → `FloorPlanAnalyzer.identify_rooms()`/`calculate_room_areas()` (`apps/dxf/services/analyzer/specialized_analyzers.py`) — Text-Keyword-Match ohne Polygon-Bezug, separat von `dxf_parser.py`s Ansatz.
- Migration dorthin ist **M-Aufwand, kein reiner Funktionstausch**: `nl2cads` Raumerkennung existiert nur als Teil eines vollen `DXFParser.parse()`-Laufs (liefert `DXFModel.rooms`), nicht als Stand-alone-Funktion auf einem bestehenden `ezdxf.Modelspace`. `CADLoaderService` müsste intern einen nl2cad-Parse-Lauf halten statt (wie heute) nur rohes `self.msp` zu wrappen.
- JSON-Contract zu Templates bleibt beim Umbau identisch (`nl2cad.core.DXFRoom` hat `name`/`layer`/`area_m2`/`perimeter_m`/`vertices`/`position` — mappt auf die bestehenden zwei Dict-Formen). **Eine sichtbare Verhaltensänderung ist einzukalkulieren**: `area_m2`/`perimeter_m` sind einheitenkorrigiert (über `$INSUNITS` + Geo-Heuristik), cad-hubs heutige Werte sind roh in Zeichnungseinheiten — bei Nicht-Meter-Dateien ändern sich die angezeigten Zahlen (Richtung: korrekter).
- **Offen bei Session-Ende:** Owner-Bestätigung zu diesem revidierten Scope stand noch aus, als die Session per `/session-ende` beendet wurde. Nächster Schritt: Go einholen, dann `CADLoaderService` umbauen.

**Bewusst zurückgestellt (Owner-Entscheidung 2026-07-08, siehe nl2cad ADR-012 §2.5):**
- `apps/ifc/services/dxf_export_service.py` bleibt unverändert in cad-hub — kein echter Geometrie-Export (schematische Rechteck-Aneinanderreihung), sondern Daten-Reporting (Issue #2). Kein Migrationskandidat.
