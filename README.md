# CAD Hub (nl2cad.de)

IFC/DXF Analysis, Fire Safety (Brandschutz), and Tendering (AVB) Platform.

Extracted from `bfagent/apps/cad_hub/` per [ADR-029](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-029-cad-hub-extraction.md).

## Quick Start (Development)

```bash
# Clone
git clone git@github.com:achimdehnert/cad-hub.git
cd cad-hub

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Setup
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Apps

| App | Description |
|-----|-------------|
| `core` | Organization, auth, health endpoints, LLM client, MCP bridge |
| `ifc` | IFC models, parser, views, handlers, tasks |
| `dxf` | DXF/DWG parsing, rendering, NL2DXF, NL2CAD |
| `areas` | DIN 277, WoFlV calculators |
| `brandschutz` | Fire safety models, analysis, reports |
| `avb` | Tendering (Ausschreibung, Vergabe, Bauausführung) |
| `export` | Excel, GAEB export services |

## Production Deployment

| Parameter | Value |
|-----------|-------|
| URL | https://nl2cad.de |
| App-Server | 46.225.113.1 (dev-server, Docker Port 8094) |
| Proxy/SSL | 88.198.191.108 (Nginx + Let's Encrypt) |
| Image | ghcr.io/achimdehnert/cad-hub/cad-hub-web:latest |
| Health | https://nl2cad.de/livez/ |
| .env.prod | /opt/cad-hub/.env.prod (auf App-Server) |

### CI/CD

- **CI** (GitHub-hosted): Lint (Ruff) → Security Scan (Bandit) → Docker Build & Push → GHCR
- **CD** (self-hosted runner auf 46.225.113.1): Pull → DB/Redis starten → Migrate → Web/Worker neu starten

```bash
# Manuellen Deploy triggern
gh workflow run cd-production.yml
```

### Lokales Setup (Entwicklung)

```bash
git clone git@github.com:achimdehnert/cad-hub.git
cd cad-hub
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Platform-Packages sind in vendor/ (kein separater Install nötig)
export PYTHONPATH=$PWD/vendor
cp .env.prod.example .env
python manage.py migrate
python manage.py runserver
```

### Platform-Packages (vendor/)

Die folgenden Packages sind direkt in `vendor/` eingecheckt (kein git-URL-Install):

| Package | Quelle |
|---------|--------|
| `chat_agent` | platform/packages/chat-agent |
| `creative_services` | platform/packages/creative-services |
| `django_tenancy` | platform/packages/django-tenancy |

Bei Updates: `cp -r /path/to/platform/packages/<pkg>/src/<pkg> vendor/`

## Architecture

See [ADR-029](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-029-cad-hub-extraction.md) for full details.
