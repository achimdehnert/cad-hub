"""Core models: Organization and Membership for multi-tenancy."""
import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Tenant organization for multi-tenancy."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Tenant identifier for data isolation",
    )
    name = models.CharField(max_length=255, verbose_name="Name")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Subdomain slug",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisation"
        verbose_name_plural = "Organisationen"

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    """Links users to organizations with a role."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        MEMBER = "member", "Mitglied"
        VIEWER = "viewer", "Betrachter"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "organization"]
        verbose_name = "Mitgliedschaft"
        verbose_name_plural = "Mitgliedschaften"

    def __str__(self) -> str:
        return f"{self.user} → {self.organization} ({self.role})"
