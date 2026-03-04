---
description: cad-hub auf Production deployen — Image bauen, migrate, seed, health check
---

## Kontext

- **Repo:** `achimdehnert/cad-hub`
- **Server:** Hetzner `88.198.191.108`, Compose-Datei: `/opt/cad-hub/docker-compose.prod.yml`
- **Container:** `cad_hub_web` (Port 8094), `cad_hub_worker`, `cad_hub_db`, `cad_hub_redis`
- **Deploy-Mechanismus:** GitHub Actions self-hosted runner (`cd-production.yml`)
- **Health-URL:** `http://127.0.0.1:8094/livez/`

---

## Schritt 1 — Sicherstellen dass alle Änderungen gepusht sind

// turbo
Führe aus:
```bash
git -C /home/dehnert/github/cad-hub status
git -C /home/dehnert/github/cad-hub push origin main
```

Erwartung: `Everything up-to-date` oder erfolgreicher Push.

---

## Schritt 2 — GitHub Actions CD-Workflow triggern

Nutze das `mcp5_cicd_manage` Tool:

```
action: dispatch
owner: achimdehnert
repo: cad-hub
workflow_id: cd-production.yml
ref: main
```

Der self-hosted Runner auf dem Hetzner-Server übernimmt:
- `docker compose pull web`
- `docker compose up migrate` (inkl. `import_registry_seed` ab v2.0.0)
- `docker compose up -d --force-recreate web worker`
- `collectstatic`
- Health check auf `http://127.0.0.1:8094/livez/`

---

## Schritt 3 — Deploy-Status prüfen

Nutze `mcp5_cicd_manage`:
```
action: workflow_runs
owner: achimdehnert
repo: cad-hub
workflow_id: cd-production.yml
per_page: 1
```

Warte bis `status: completed` und `conclusion: success`.

---

## Schritt 4 — Health Check bestätigen

Prüfe:
```
mcp5_docker_manage:
  action: container_status
  host: 88.198.191.108
  container_id: cad_hub_web
```

Oder HTTP-Check:
```
mcp5_ssh_manage:
  action: http_check
  host: 88.198.191.108
  url: http://127.0.0.1:8094/livez/
  expect_status: 200
```

---

## Schritt 5 — Registry Seed prüfen (nur beim ersten Deploy nach v2.0.0)

Falls `import_registry_seed` noch nicht ausgeführt wurde:
```
mcp5_docker_manage:
  action: container_exec
  host: 88.198.191.108
  container_id: cad_hub_web
  command: python manage.py import_registry_seed --dry-run
```

Bei OK ohne `--dry-run` nochmal ausführen.

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| `GITHUB_TOKEN not set` | MCP-Tool kann nicht dispatchen — GitHub Actions manuell im Browser triggern: https://github.com/achimdehnert/cad-hub/actions/workflows/cd-production.yml |
| `compose file not found` | Immer `-f docker-compose.prod.yml` angeben, nie Default |
| Health check schlägt fehl | `container_logs container_id=cad_hub_web lines=50` prüfen |
| Migration fehlgeschlagen | `container_logs container_id=cad-hub-migrate-1 lines=50` prüfen |
