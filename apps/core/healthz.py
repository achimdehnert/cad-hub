"""
Health endpoints for container orchestration (ADR-022).

These endpoints are exempt from authentication and tenant resolution.
They MUST be accessible without a subdomain for Docker healthchecks
and load balancer probes to function correctly.

Registration in config/urls.py:
    urlpatterns = [
        path("livez/", liveness, name="health-liveness"),
        path("healthz/", readiness, name="health-readiness"),
    ]

The SubdomainTenantMiddleware MUST exclude these paths.
See HEALTH_PATHS constant below.
"""
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

HEALTH_PATHS = frozenset({"/livez/", "/healthz/", "/health/"})


@csrf_exempt
@require_GET
def liveness(request):
    """Liveness probe: Is the process alive?"""
    return JsonResponse({"status": "alive"})


@csrf_exempt
@require_GET
def readiness(request):
    """Readiness probe: Can we serve traffic?"""
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = str(e)
        return JsonResponse(
            {"status": "unhealthy", "checks": checks},
            status=503,
        )

    return JsonResponse({"status": "healthy", "checks": checks})
