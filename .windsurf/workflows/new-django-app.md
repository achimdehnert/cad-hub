---
description: Neues Django-App-Skeleton mit Platform-Konventionen anlegen (cad-hub)
version: "1.0"
last_reviewed: 2026-03-06
review_interval_days: 90
scope: cad-hub
---

Inputs: App-Name (snake_case), kurze Beschreibung.

HINWEIS: cad-hub verwendet BARE Modulnamen (kein `apps.`-Präfix) im `src/`-Verzeichnis.

1. Prüfen ob App bereits existiert:
   // turbo
   ```bash
   ls src/{app_name}/ 2>/dev/null
   ```
   Falls Verzeichnis vorhanden: STOP — "App existiert bereits."

2. Verzeichnisstruktur anlegen:
   ```bash
   mkdir -p src/{app_name}/tests
   mkdir -p src/templates/{app_name}
   touch src/{app_name}/__init__.py
   touch src/{app_name}/models.py
   touch src/{app_name}/views.py
   touch src/{app_name}/urls.py
   touch src/{app_name}/admin.py
   touch src/{app_name}/services.py
   touch src/{app_name}/tests/__init__.py
   ```

3. `apps.py` mit `default_auto_field = "django.db.models.BigAutoField"` und `name = "{app_name}"` erstellen.

4. `urls.py` mit `app_name = "{app_name}"` und leeren `urlpatterns` erstellen.

5. In `config/settings/base.py` unter `INSTALLED_APPS` eintragen: `"{app_name}"`

6. In `config/urls.py` eintragen:
   `path("{app_name}/", include("{app_name}.urls"))`

7. Initiale Migration erstellen:
   ```bash
   python manage.py makemigrations {app_name}
   ```

8. Prüfen:
   // turbo
   ```bash
   python manage.py check
   ```

9. Zusammenfassung ausgeben: "App src/{app_name}/ erstellt."
