---
description: Quality Gate vor Publish/Deploy
---

# Repo Health Check

## django-app
```bash
for f in Makefile docker-compose.prod.yml .env.example requirements.txt; do
  [ -e "$f" ] && echo OK || echo "MISSING: $f"
done
```
- [ ] CI: Tests vor Build+Deploy
- [ ] `/livez/` vorhanden
- [ ] pytest grün

```bash
python3 ~/github/platform/tools/repo_health_check.py --profile django-app --path .
```
