"""Production settings — security hardened, env-driven."""

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="").split(",")
# ADR-021: Internal hosts for Docker/LB health probes — always present
ALLOWED_HOSTS.extend(h for h in ("localhost", "127.0.0.1") if h not in ALLOWED_HOSTS)

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = False  # Nginx handles SSL termination
SECURE_REDIRECT_EXEMPT = [r"^livez/$", r"^healthz/$"]
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
