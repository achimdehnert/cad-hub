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

```bash
# On server (88.198.191.108)
cd /opt/cad-hub
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

| Parameter | Value |
|-----------|-------|
| Domain | nl2cad.de |
| Port | 8094 |
| Health | /livez/, /healthz/ |
| GHCR | ghcr.io/achimdehnert/cad-hub |

## Architecture

See [ADR-029](https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-029-cad-hub-extraction.md) for full details.
