# Agent PR Checkliste (ADR-086)

## Verlinktes Issue

Closes #<!-- Issue-Nummer -->

## Task-Typ

<!-- feature | bugfix | refactor | test | infra | adr -->

## Zusammenfassung

<!-- Was wurde implementiert? (≤ 500 Zeichen) -->

## Acceptance Criteria

- [ ] Criterion 1

## Scope-Check (ADR-081)

- [ ] Nur Dateien in `affected_paths` geändert
- [ ] Keine `migrations/` automatisch erstellt
- [ ] Keine `.env*`, `config/settings/prod*` geändert

## Quality Gates

- [ ] `pytest` → 0 Failures
- [ ] `ruff check` → 0 Errors
- [ ] Coverage-Delta ≥ 0%

## Django-Compliance

- [ ] Views → Services → Models
- [ ] Templates erweitern `base.html`
- [ ] HTMX für Interaktionen
- [ ] `tenant_id` in allen Queries
- [ ] `CHANGELOG.md` aktualisiert

## Test-Nachweis

```
# pytest tests/MODULE/ -v --tb=short
```
