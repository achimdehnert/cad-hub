"""
CAD Hub - Test Settings (ADR-179: PostgreSQL-Only Testing)
"""

from decouple import config as decouple_config

from .base import *  # noqa: F401,F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # Defaults match the platform reusable CI workflow's postgres
        # service (_ci-python.yml: test_user/test_pass/test_db; exports
        # POSTGRES_HOST + POSTGRES_PORT — Port ist seit shared-ci#8
        # ephemer). TEST_DB_* still override for local dev.
        "NAME": decouple_config("TEST_DB_NAME", default="test_db"),
        "USER": decouple_config("TEST_DB_USER", default="test_user"),
        "PASSWORD": decouple_config("TEST_DB_PASSWORD", default="test_pass"),
        "HOST": decouple_config(
            "TEST_DB_HOST",
            default=decouple_config("POSTGRES_HOST", default="localhost"),
        ),
        "PORT": decouple_config(
            "TEST_DB_PORT",
            default=decouple_config("POSTGRES_PORT", default="5432"),
        ),
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
