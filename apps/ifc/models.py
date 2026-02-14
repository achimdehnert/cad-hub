"""
IFC models — project, model, floor, room, window, door, wall, slab.

Source: bfagent/apps/cad_hub/models/ifc.py
Changes: app_label → ifc, tenant_id added to all models.
"""
import uuid

from django.conf import settings
from django.db import models


class IFCProject(models.Model):
    """IFC Project - UI Cache Only

    IMPORTANT: This is NOT the source of truth!
    Real data lives in IFC MCP Backend (PostgreSQL).
    This model only caches data for UI performance.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Same UUID as IFC MCP Backend",
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )

    name = models.CharField(
        max_length=255, verbose_name="Projektname"
    )

    mcp_project_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="IFC MCP Projekt-ID",
        help_text="Reference to IFC MCP Backend",
    )

    cached_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Cached Project Data",
        help_text="Cached data from IFC MCP API",
    )
    cached_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Cache Timestamp"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="UI User",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ifc"
        ordering = ["-updated_at"]
        verbose_name = "IFC Projekt (Cache)"
        verbose_name_plural = "IFC Projekte (Cache)"

    def __str__(self) -> str:
        return self.name

    @property
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid (< 1 hour)."""
        if not self.cached_at:
            return False
        from datetime import timedelta

        from django.utils import timezone

        return timezone.now() - self.cached_at < timedelta(hours=1)

    @property
    def model_count(self) -> int:
        """Count of models in this project."""
        return self.models.count()


class IFCModel(models.Model):
    """Eine Version eines IFC-Modells."""

    class Status(models.TextChoices):
        UPLOADING = "uploading", "Wird hochgeladen"
        PROCESSING = "processing", "Wird verarbeitet"
        READY = "ready", "Bereit"
        ERROR = "error", "Fehler"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    project = models.ForeignKey(
        IFCProject,
        on_delete=models.CASCADE,
        related_name="models",
        verbose_name="Projekt",
    )
    version = models.PositiveIntegerField(
        default=1, verbose_name="Version"
    )

    ifc_file = models.FileField(
        upload_to="ifc_models/%Y/%m/",
        verbose_name="IFC Datei",
    )
    xkt_file = models.FileField(
        upload_to="ifc_models/%Y/%m/",
        blank=True,
        verbose_name="XKT Datei (3D Viewer)",
    )

    ifc_schema = models.CharField(
        max_length=20, blank=True, verbose_name="IFC Schema"
    )
    application = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Erstellungs-Software",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADING,
        verbose_name="Status",
    )
    error_message = models.TextField(
        blank=True, verbose_name="Fehlermeldung"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "ifc"
        ordering = ["-version"]
        unique_together = ["project", "version"]
        verbose_name = "IFC Modell"
        verbose_name_plural = "IFC Modelle"

    def __str__(self) -> str:
        return f"{self.project.name} v{self.version}"


class Floor(models.Model):
    """Geschoss (IfcBuildingStorey)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_model = models.ForeignKey(
        IFCModel,
        on_delete=models.CASCADE,
        related_name="floors",
        verbose_name="IFC Modell",
    )

    ifc_guid = models.CharField(
        max_length=36, verbose_name="IFC GUID"
    )

    name = models.CharField(
        max_length=100, verbose_name="Name"
    )
    code = models.CharField(
        max_length=20, blank=True, verbose_name="Kurzbezeichnung"
    )
    elevation = models.FloatField(
        default=0, verbose_name="Höhe (m)"
    )

    sort_order = models.IntegerField(default=0)

    class Meta:
        app_label = "ifc"
        ordering = ["sort_order", "elevation"]
        verbose_name = "Geschoss"
        verbose_name_plural = "Geschosse"

    def __str__(self) -> str:
        return f"{self.name} ({self.elevation:+.2f}m)"


class Room(models.Model):
    """Raum (IfcSpace)."""

    class UsageCategory(models.TextChoices):
        """DIN 277 Nutzungskategorien."""

        NF1_1 = "NF1.1", "NF 1.1 - Wohnen/Aufenthalt"
        NF1_2 = "NF1.2", "NF 1.2 - Büroarbeit"
        NF1_3 = "NF1.3", "NF 1.3 - Produktion"
        NF2 = "NF2", "NF 2 - Büroflächen"
        NF3 = "NF3", "NF 3 - Lager/Verteilen"
        NF4 = "NF4", "NF 4 - Bildung/Kultur"
        NF5 = "NF5", "NF 5 - Heilen/Pflegen"
        NF6 = "NF6", "NF 6 - Sonstige"
        TF7 = "TF7", "TF 7 - Technikflächen"
        VF8 = "VF8", "VF 8 - Verkehrsflächen"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_model = models.ForeignKey(
        IFCModel,
        on_delete=models.CASCADE,
        related_name="rooms",
        verbose_name="IFC Modell",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="rooms",
        null=True,
        blank=True,
        verbose_name="Geschoss",
    )

    ifc_guid = models.CharField(
        max_length=36, verbose_name="IFC GUID"
    )

    number = models.CharField(
        max_length=20, verbose_name="Raumnummer"
    )
    name = models.CharField(
        max_length=100, verbose_name="Raumname"
    )
    long_name = models.CharField(
        max_length=255, blank=True, verbose_name="Langname"
    )

    area = models.FloatField(
        default=0, verbose_name="Fläche (m²)"
    )
    height = models.FloatField(
        default=0, verbose_name="Höhe (m)"
    )
    volume = models.FloatField(
        default=0, verbose_name="Volumen (m³)"
    )
    perimeter = models.FloatField(
        default=0, verbose_name="Umfang (m)"
    )

    usage_category = models.CharField(
        max_length=10,
        choices=UsageCategory.choices,
        blank=True,
        verbose_name="Nutzungsart (DIN 277)",
    )

    class Meta:
        app_label = "ifc"
        ordering = ["floor__sort_order", "number"]
        verbose_name = "Raum"
        verbose_name_plural = "Räume"

    def __str__(self) -> str:
        return f"{self.number} - {self.name}"



# Re-export component models for backward compatibility
from .models_components import Door, Slab, Wall, Window  # noqa: F401
