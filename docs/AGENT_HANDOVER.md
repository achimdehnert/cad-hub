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
