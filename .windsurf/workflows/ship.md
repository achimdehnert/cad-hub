---
description: cad-hub auf Production deployen — verify, push, CI, migrate, seed, health check
version: "2.0"
last_reviewed: 2026-03-04
review_interval_days: 90
scope: cad-hub
health_port: 8094
cd_workflow: cd-production.yml
web_container: cad_hub_web
---

## Schritt 1 — Branch + Status verifizieren

**KEIN auto-run. User-Bestätigung vor Push erforderlich.**

```bash
git -C /home/dehnert/github/cad-hub branch --show-current
git -C /home/dehnert/github/cad-hub status
git -C /home/dehnert/github/cad-hub diff --stat HEAD
```

Erwartung: Branch = `main`, keine uncommitted WIP-Änderungen.
**Abbruch wenn:** Branch != main ODER uncommitted Änderungen vorhanden.

---

## Schritt 2 — Änderungen pushen

Erst nach User-Bestätigung aus Schritt 1:

// turbo
```bash
git -C /home/dehnert/github/cad-hub push origin main
```

---

## Schritt 3 — GitHub Actions CD-Workflow triggern

```
mcp5_cicd_manage:
  action: dispatch
  owner: achimdehnert
  repo: cad-hub
  workflow_id: cd-production.yml
  ref: main
```

Self-hosted Runner übernimmt:
1. `docker compose pull web`
2. `docker compose up migrate`
3. `python manage.py import_registry_seed` (idempotent)
4. `docker compose up -d --force-recreate web worker`
5. `collectstatic`
6. Health check `/livez/`

---

## Schritt 4 — Deploy-Status verfolgen

```
mcp5_cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: cad-hub
  workflow_id: cd-production.yml
  per_page: 1
```

Warte auf `conclusion: success`. Bei `failure` → Schritt 6 (Rollback).

---

## Schritt 5 — Health Check

```
mcp5_ssh_manage:
  action: http_check
  host: ${{ secrets.PROD_SERVER_IP }}
  url: http://127.0.0.1:8094/livez/
  expect_status: 200
```

---

## Schritt 6 — Rollback (nur bei Health-Check-Failure)

```bash
docker compose -f docker-compose.prod.yml pull web:<previous-tag>
docker compose -f docker-compose.prod.yml up -d --force-recreate web worker
```

Dann Health Check wiederholen.

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Migration fehlgeschlagen | `container_logs container_id=cad-hub-migrate-1 lines=80` |
| Seed fehlgeschlagen | `container_exec container_id=cad_hub_web command="python manage.py import_registry_seed --dry-run"` |
| Health check schlägt fehl | `container_logs container_id=cad_hub_web lines=80` |
| Image nicht aktuell | `workflow_runs repo=cad-hub workflow_id=ci.yml` prüfen |
| Branch falsch | `git checkout main && git pull origin main` |
