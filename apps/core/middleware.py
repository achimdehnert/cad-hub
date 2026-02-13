"""Subdomain tenant resolution middleware."""
import logging

from django.http import HttpRequest, HttpResponse

from .healthz import HEALTH_PATHS

logger = logging.getLogger(__name__)


class SubdomainTenantMiddleware:
    """Resolves tenant_id from subdomain. Excludes health paths."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip health endpoints
        if request.path in HEALTH_PATHS:
            return self.get_response(request)

        # Extract subdomain
        host = request.get_host().split(":")[0]
        parts = host.split(".")

        # subdomain.nl2cad.de → parts = ["subdomain", "nl2cad", "de"]
        if len(parts) > 2:
            subdomain = parts[0]
            if subdomain != "www":
                self._resolve_tenant(request, subdomain)
        else:
            request.tenant_id = None
            request.organization = None

        return self.get_response(request)

    def _resolve_tenant(
        self, request: HttpRequest, subdomain: str
    ) -> None:
        """Resolve organization from subdomain slug."""
        from .models import Organization

        try:
            org = Organization.objects.get(slug=subdomain)
            request.tenant_id = org.tenant_id
            request.organization = org
        except Organization.DoesNotExist:
            logger.warning("Unknown subdomain: %s", subdomain)
            request.tenant_id = None
            request.organization = None
