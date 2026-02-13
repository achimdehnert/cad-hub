"""Tenant-aware manager for multi-tenancy query filtering."""
import uuid

from django.db import models


class TenantAwareManager(models.Manager):
    """Manager that provides tenant-scoped querysets."""

    def for_tenant(self, tenant_id: uuid.UUID) -> models.QuerySet:
        """Filter queryset by tenant_id."""
        return self.filter(tenant_id=tenant_id)
