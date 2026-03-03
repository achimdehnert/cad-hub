# cad-hub — Agent Handover Document

> **ADR-086-konform** | Zuletzt aktualisiert: 2026-03-03 | Review-Intervall: 30 Tage

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
