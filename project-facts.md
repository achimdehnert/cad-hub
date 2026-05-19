# Project Facts: cad-hub

> Auto-generiert von `platform/.github/scripts/push_project_facts.py`
> Letzte Aktualisierung: 2026-05-18 — bei Änderungen: `platform/gen-project-facts.yml` triggern

## Meta

- **Type**: `django`
- **GitHub**: `https://github.com/achimdehnert/cad-hub`
- **Branch**: `main` — push: `git push` (SSH-Key konfiguriert)

## Lokale Umgebung (Dev Desktop — adehnert)

- **Pfad**: `~/CascadeProjects/cad-hub` → `$GITHUB_DIR` = `~/CascadeProjects`
- **src_root**: `./` (root) — `manage.py` liegt dort
- **pythonpath**: `./`
- **Venv**: `~/CascadeProjects/cad-hub/.venv/bin/python`
- **MCP aktiv**: `mcp0_` = github · `mcp1_` = orchestrator

## Settings

- **Prod-Modul**: `config.settings.production`
- **Test-Modul**: `config.settings.test`
- **Testpfad**: `tests/`

## Stack

- **Django**: `4.8`
- **Python**: `3.12`
- **PostgreSQL**: `16`
- **HTMX installiert**: nein
- **HTMX-Detection**: `request.headers.get("HX-Request") == "true"`


## Apps

- `accounts`
- `areas`
- `avb`
- `brandschutz`
- `core`
- `dxf`
- `export`
- `ifc`
- `registry`

## Infrastruktur

- **Prod-URL**: `nl2cad.de`
- **Staging-URL**: `staging.nl2cad.de`
- **Port**: `8094`
- **Health-Endpoint**: `/livez/`
- **DB-Name**: `cad_hub`

## System (Hetzner Server)

- devuser hat **KEIN sudo-Passwort** → System-Pakete immer via SSH als root:
  ```bash
  ssh root@localhost "apt-get install -y <package>"
  ```
