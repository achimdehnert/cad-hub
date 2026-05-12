"""
CAD Hub - Test Settings (ADR-179: PostgreSQL-Only Testing)

USE_POSTGRES=0 in CI falls back to SQLite for unit tests without DB service.
Integration/contract tests should always use PostgreSQL.
"""

from decouple import config as decouple_config

from .base import *  # noqa: F401,F403

DEBUG = False

if decouple_config("USE_POSTGRES", default="1") == "0":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": decouple_config("TEST_DB_NAME", default="cad_hub_test"),
            "USER": decouple_config("TEST_DB_USER", default="dehnert"),
            "PASSWORD": decouple_config("TEST_DB_PASSWORD", default=""),
            "HOST": decouple_config("TEST_DB_HOST", default="localhost"),
            "PORT": decouple_config("TEST_DB_PORT", default="5434"),
            "TEST": {"NAME": "test_cad_hub"},
        }
    }

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
