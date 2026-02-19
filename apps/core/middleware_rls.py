"""
TenantRLSMiddleware — setzt PostgreSQL session variable für RLS-Policies.

Muss NACH SubdomainTenantMiddleware in MIDDLEWARE stehen.
Setzt SET LOCAL app.current_tenant_id pro Request.
"""
from django.db import connection


class TenantRLSMiddleware:
    """Setzt PostgreSQL session variable für RLS-Policies.

    Muss NACH SubdomainTenantMiddleware in MIDDLEWARE kommen.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [str(tenant_id)],
                )
        return self.get_response(request)
