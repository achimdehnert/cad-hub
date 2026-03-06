---
description: Lint, Tests und Coverage für cad-hub ausführen
version: "1.0"
last_reviewed: 2026-03-06
review_interval_days: 90
scope: cad-hub
---

## Schritt 1 — Ruff Lint + Format

// turbo
```bash
ruff check src/ --output-format=concise
ruff format --check src/
```

Bei Fehlern: `ruff check src/ --fix && ruff format src/` ausführen.

---

## Schritt 2 — Tests + Coverage

// turbo
```bash
python -m pytest \
  --tb=short \
  --no-header \
  -q \
  --cov=src \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=70
```

Erwartung: alle Tests grün, Coverage ≥ 70%.

---

## Schritt 3 — Django System Check

// turbo
```bash
DJANGO_SETTINGS_MODULE=config.settings_test python -m django check --deploy --fail-level WARNING
```

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Import-Fehler | `pip install -r requirements.txt -r requirements-dev.txt` |
| DB nicht erreichbar | PostgreSQL lokal starten oder `DATABASE_URL` prüfen |
| Coverage zu niedrig | `--cov-report=html` → `htmlcov/index.html` öffnen |
