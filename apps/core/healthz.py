"""Health endpoints: re-export from django_tenancy (ADR-035).

Now uses the shared implementation with DB + Redis + latency checks.
"""

from django_tenancy.healthz import HEALTH_PATHS, liveness, readiness

__all__ = ["HEALTH_PATHS", "liveness", "readiness"]
