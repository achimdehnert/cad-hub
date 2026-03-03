---
description: Agent Task ausführen — ADR-086-konformer Sprint-Workflow für cad-hub
source_adr: ADR-086
last_reviewed: 2026-03-03
review_interval_days: 30
version: "1.0"
---

# cad-hub — Agent Task Workflow (ADR-086)

## Schritt 0: Pflicht-Setup

1. Lies `docs/AGENT_HANDOVER.md` — Repo-Kontext
2. Lies das verlinkte GitHub Issue
3. Baseline-Check:

```bash
pytest --tb=short -q 2>&1 | tail -5
ruff check . 2>&1 | tail -3
```

## Schritt 1: Scope-Lock (ADR-081)

- Erlaubt: nur `affected_paths` aus Issue
- Verboten: `migrations/`, `.env*`, `config/settings/prod*`, `*.pem`, `*.key`

## Schritt 2: Feature-Branch

```bash
git checkout -b ai/developer/<task-id>
```

## Schritt 3: Implementieren

1. Model in `models.py` (mit `tenant_id`)
2. Service in `services.py`
3. View in `views.py` (nur HTTP)
4. Template erweitert `base.html` + HTMX
5. Tests in `tests/`
6. `CHANGELOG.md` unter `[Unreleased]`

## Schritt 4: Quality Gates

```bash
pytest tests/MODULE/ -v --tb=short
ruff check .
```

## Schritt 5: PR

```bash
git push -u origin ai/developer/<task-id>
```

PR-Body: `.github/PULL_REQUEST_TEMPLATE/agent-pr.md` ausfüllen.
