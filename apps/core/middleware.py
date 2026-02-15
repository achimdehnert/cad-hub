"""Subdomain tenant resolution: re-export from django_tenancy (ADR-035)."""

from django_tenancy.middleware import SubdomainTenantMiddleware

__all__ = ["SubdomainTenantMiddleware"]
