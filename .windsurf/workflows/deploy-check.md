---
description: Pre-deployment verification checklist
---

# Deploy-Check

// turbo
```bash
git log --oneline -3 && git status
pytest tests/ -q --tb=short 2>&1 | tail -10
python manage.py migrate --check
```

- [ ] Tests grün, CI grün
- [ ] Destructive Migration? → Backup zuerst
- [ ] `.env.prod` aktuell

```bash
curl -sf https://[DOMAIN]/livez/ && echo OK
```
