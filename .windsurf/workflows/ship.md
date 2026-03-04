---
description: cad-hub auf Production deployen — Image bauen, migrate, seed, health check
---

## Kontext

- **Repo:** `achimdehnert/cad-hub`
- **Server:** `88.198.191.108`, Pfad: `/opt/cad-hub`
- **Compose:** `docker-compose.prod.yml`
- **Web-Container:** `cad_hub_web` (Port 8094)
- **Deploy-Mechanismus:** GitHub Actions `cd-production.yml` (self-hosted runner `hetzner/dev`)
- **Health-URL:** `http://127.0.0.1:8094/livez/`

---

## Schritt 1 — Änderungen pushen

// turbo
```bash
git -C /home/dehnert/github/cad-hub status
git -C /home/dehnert/github/cad-hub push origin main
```

---

## Schritt 2 — GitHub Actions CD-Workflow triggern

```
mcp5_cicd_manage:
  action: dispatch
  owner: achimdehnert
  repo: cad-hub
  workflow_id: cd-production.yml
  ref: main
```

Der self-hosted Runner auf dem Hetzner-Server übernimmt automatisch:
1. `docker compose -f docker-compose.prod.yml pull web`
2. `docker compose -f docker-compose.prod.yml up migrate`
3. `python manage.py import_registry_seed` (idempotent)
4. `docker compose -f docker-compose.prod.yml up -d --force-recreate web worker`
5. `collectstatic`
6. Health check `http://127.0.0.1:8094/livez/`

---

## Schritt 3 — Deploy-Status prüfen

```
mcp5_cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: cad-hub
  workflow_id: cd-production.yml
  per_page: 1
```

Warte auf `conclusion: success`.

---

## Schritt 4 — Health Check bestätigen

```
mcp5_docker_manage:
  action: container_status
  host: 88.198.191.108
  container_id: cad_hub_web
```

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| `GITHUB_TOKEN not set` in MCP | GitHub Actions manuell triggern: https://github.com/achimdehnert/cad-hub/actions/workflows/cd-production.yml |
| Migration fehlgeschlagen | `container_logs container_id=cad-hub-migrate-1 lines=50 host=88.198.191.108` |
| Seed fehlgeschlagen | `container_exec container_id=cad_hub_web command="python manage.py import_registry_seed --dry-run"` |
| Health check schlägt fehl | `container_logs container_id=cad_hub_web lines=50 host=88.198.191.108` |
| Image nicht aktuell | CI muss zuerst gebaut haben — `workflow_runs repo=cad-hub workflow_id=ci.yml` prüfen |
