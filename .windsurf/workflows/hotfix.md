---
description: Schneller Produktions-Fix
---

# Hotfix

> Kein Refactoring. Kleinster möglicher Fix.

// turbo
```bash
git log --oneline -10
git checkout main && git pull
git checkout -b hotfix/$(date +%Y%m%d)-BESCHREIBUNG
```

Fix → Regression Test → `pytest tests/ -q` → PR (Squash Merge) → `/deploy`

```
[ ] Root Cause identifiziert
[ ] Minimaler Fix
[ ] Regression Test vorhanden
[ ] Tests grün
[ ] Deployed
```
