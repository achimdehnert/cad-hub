"""Tenant-aware manager: re-export from django_tenancy (ADR-035)."""

from django_tenancy.managers import TenantAwareManager

__all__ = ["TenantAwareManager"]
