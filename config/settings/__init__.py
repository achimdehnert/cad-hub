"""
Settings dispatcher — reads DJANGO_ENV to select settings module.

Default: development (for local `manage.py runserver`).
Production: set DJANGO_SETTINGS_MODULE=config.settings.production in .env.prod.
"""
import os

env = os.environ.get("DJANGO_ENV", "development")

if env == "production":
    from .production import *  # noqa: F401, F403
elif env == "test":
    from .base import *  # noqa: F401, F403
else:
    from .development import *  # noqa: F401, F403
