"""Development settings — DEBUG=True, sqlite fallback."""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# Disable tenant middleware in dev (optional)
MIDDLEWARE = [
    m for m in MIDDLEWARE  # noqa: F405
    if m != "apps.core.middleware.SubdomainTenantMiddleware"
]
