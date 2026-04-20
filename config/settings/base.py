"""
Base settings shared across all environments.
"""

import sys
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Vendor packages (django_tenancy, chat_agent, etc.) are plain Python
# packages without pyproject.toml — add vendor/ to sys.path so they
# are importable as top-level modules.
VENDOR_DIR = str(BASE_DIR / "vendor")
if VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only-change-in-production")

DEBUG = False

ALLOWED_HOSTS: list[str] = []
# ADR-021: Internal hosts for Docker/LB health probes — always present
ALLOWED_HOSTS.extend(h for h in ("localhost", "127.0.0.1") if h not in ALLOWED_HOSTS)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Platform packages
    "django_tenancy",
    # CAD Hub apps
    "apps.core",
    "apps.ifc",
    "apps.dxf",
    "apps.areas",
    "apps.brandschutz",
    "apps.avb",
    "apps.export",
    "apps.registry",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_tenancy.middleware.SubdomainTenantMiddleware",
    "apps.core.middleware_rls.TenantRLSMiddleware",
    "apps.core.htmx.HtmxErrorMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "templates" / "cad_hub"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="cad_hub"),
        "USER": config("POSTGRES_USER", default="cad_hub"),
        "PASSWORD": config("POSTGRES_PASSWORD", default=""),
        "HOST": config("POSTGRES_HOST", default="db"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}


AUTHENTICATION_BACKENDS = [
    "apps.accounts.auth.IILOIDCAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

# Registry — GitHub Actions Tenant-Onboarding
GITHUB_REGISTRY_TOKEN = config("GITHUB_REGISTRY_TOKEN", default="")
GITHUB_REGISTRY_OWNER = config("GITHUB_REGISTRY_OWNER", default="achimdehnert")
GITHUB_REGISTRY_REPO = config("GITHUB_REGISTRY_REPO", default="nl2cad")

# Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Logging (JSON for production, console for dev)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": ("%(asctime)s %(levelname)s %(name)s %(message)s"),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# --- authentik OIDC (ADR-142) ---
OIDC_RP_CLIENT_ID = config("OIDC_RP_CLIENT_ID", default="")
OIDC_RP_CLIENT_SECRET = config("OIDC_RP_CLIENT_SECRET", default="")
_OIDC_APP_SLUG = config("OIDC_APP_SLUG", default="cad-hub")
_IDP = "https://id.iil.pet/application/o"
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{_IDP}/authorize/"
OIDC_OP_TOKEN_ENDPOINT = f"{_IDP}/token/"
OIDC_OP_USER_ENDPOINT = f"{_IDP}/userinfo/"
OIDC_OP_JWKS_ENDPOINT = f"{_IDP}/{_OIDC_APP_SLUG}/jwks/"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"
LOGOUT_REDIRECT_URL = "/"
