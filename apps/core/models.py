"""Core models: re-export from django_tenancy (ADR-035).

Organization and Membership are now provided by the shared
django-tenancy package. This module re-exports them so that
existing imports like ``from apps.core.models import Organization``
continue to work.
"""

from django_tenancy.models import Membership, Organization

__all__ = ["Organization", "Membership"]
