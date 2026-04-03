"""Production settings — security hardened, env-driven."""
import os

from .base import *  # noqa: F401, F403
from decouple import config

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="").split(",")

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = False  # Nginx handles SSL termination
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF trusted origins (required behind reverse proxy)
_csrf = config("CSRF_TRUSTED_ORIGINS", default="")
if _csrf:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(",") if o.strip()]

# Redis (for Chat-Agent session backend)
REDIS_URL = config("REDIS_URL", default="redis://redis:6379/1")
