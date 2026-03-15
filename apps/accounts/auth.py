"""OIDC Authentication Backend — authentik Integration (ADR-142).

Platform-wide OIDC backend with:
- Soft-Delete-aware User-Lookup (is_active=True)
- JIT-Provisioning (create user on first OIDC login)
- Name sync on every login

Requires: mozilla-django-oidc>=4.0
"""
from __future__ import annotations

import logging

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class IILOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Platform OIDC backend for authentik (ADR-142)."""

    def filter_users_by_claims(self, claims):
        """Find active (non-deactivated) users by email."""
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(
            email__iexact=email,
            is_active=True,
        )

    def create_user(self, claims):
        """Create new user on first OIDC login (JIT-Provisioning)."""
        email = claims.get("email", "")
        if not email:
            logger.warning("OIDC create_user: no email in claims")
            return None

        user = super().create_user(claims)
        user.first_name = claims.get("given_name", "")[:150]
        user.last_name = claims.get("family_name", "")[:150]
        user.is_active = True
        user.save(
            update_fields=["first_name", "last_name", "is_active"],
        )

        logger.info(
            "OIDC user created",
            extra={"email": email, "sub": claims.get("sub", "")},
        )
        return user

    def update_user(self, user, claims):
        """Sync name on every login."""
        user = super().update_user(user, claims)
        updated = False
        new_first = claims.get("given_name", "")[:150]
        new_last = claims.get("family_name", "")[:150]

        if new_first and user.first_name != new_first:
            user.first_name = new_first
            updated = True
        if new_last and user.last_name != new_last:
            user.last_name = new_last
            updated = True
        if updated:
            user.save(update_fields=["first_name", "last_name"])
        return user
