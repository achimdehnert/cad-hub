"""
AVB models — Ausschreibung, Vergabe, Bauausführung.

Source: bfagent/apps/cad_hub/models_avb.py
Changes: app_label → avb, tenant_id added, FK → ifc.IFCProject.
"""
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProjectPhase(models.TextChoices):
    """HOAI Leistungsphasen"""

    LP1 = "LP1", "LP1 - Grundlagenermittlung"
    LP2 = "LP2", "LP2 - Vorplanung"
    LP3 = "LP3", "LP3 - Entwurfsplanung"
    LP4 = "LP4", "LP4 - Genehmigungsplanung"
    LP5 = "LP5", "LP5 - Ausführungsplanung"
    LP6 = "LP6", "LP6 - Vorbereitung der Vergabe"
    LP7 = "LP7", "LP7 - Mitwirkung bei der Vergabe"
    LP8 = "LP8", "LP8 - Objektüberwachung"
    LP9 = "LP9", "LP9 - Objektbetreuung"


class TenderStatus(models.TextChoices):
    DRAFT = "draft", "Entwurf"
    PUBLISHED = "published", "Veröffentlicht"
    SUBMISSION = "submission", "Angebotsphase"
    EVALUATION = "evaluation", "Auswertung"
    AWARDED = "awarded", "Vergeben"
    CANCELLED = "cancelled", "Abgebrochen"


class BidStatus(models.TextChoices):
    INVITED = "invited", "Eingeladen"
    RECEIVED = "received", "Eingegangen"
    EVALUATED = "evaluated", "Ausgewertet"
    NEGOTIATION = "negotiation", "Verhandlung"
    AWARDED = "awarded", "Zuschlag"
    REJECTED = "rejected", "Abgelehnt"


class CostGroup(models.TextChoices):
    """DIN 276 Kostengruppen (Auszug)"""

    KG100 = "100", "100 - Grundstück"
    KG200 = "200", "200 - Vorbereitende Maßnahmen"
    KG300 = "300", "300 - Bauwerk - Baukonstruktionen"
    KG310 = "310", "310 - Baugrube/Erdbau"
    KG320 = "320", "320 - Gründung"
    KG330 = "330", "330 - Außenwände"
    KG340 = "340", "340 - Innenwände"
    KG350 = "350", "350 - Decken"
    KG360 = "360", "360 - Dächer"
    KG370 = "370", "370 - Infrastruktur"
    KG390 = "390", "390 - Sonstige Baukonstruktionen"
    KG400 = "400", "400 - Bauwerk - Technische Anlagen"
    KG410 = "410", "410 - Abwasser/Wasser/Gas"
    KG420 = "420", "420 - Wärmeversorgung"
    KG430 = "430", "430 - Lüftung"
    KG440 = "440", "440 - Elektro"
    KG450 = "450", "450 - Fernmelde"
    KG460 = "460", "460 - Förderanlagen"
    KG470 = "470", "470 - Nutzungsspezifische Anlagen"
    KG480 = "480", "480 - Gebäudeautomation"
    KG500 = "500", "500 - Außenanlagen"
    KG600 = "600", "600 - Ausstattung"
    KG700 = "700", "700 - Baunebenkosten"


class ConstructionProject(models.Model):
    """Erweitertes Bauprojekt für Planung & Ausschreibung."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_project = models.OneToOneField(
        "ifc.IFCProject",
        on_delete=models.CASCADE,
        related_name="construction_project",
        verbose_name="IFC Projekt",
    )
    project_number = models.CharField(
        max_length=50, blank=True, verbose_name="Projektnummer"
    )
    client = models.CharField(
        max_length=255, verbose_name="Auftraggeber"
    )
    client_contact = models.CharField(
        max_length=255, blank=True,
        verbose_name="Ansprechpartner AG",
    )
    street = models.CharField(
        max_length=255, blank=True, verbose_name="Straße"
    )
    zip_code = models.CharField(
        max_length=10, blank=True, verbose_name="PLZ"
    )
    city = models.CharField(
        max_length=100, blank=True, verbose_name="Ort"
    )
    current_phase = models.CharField(
        max_length=10,
        choices=ProjectPhase.choices,
        default=ProjectPhase.LP1,
        verbose_name="Aktuelle Phase",
    )
    planning_start = models.DateField(
        null=True, blank=True, verbose_name="Planungsbeginn"
    )
    construction_start = models.DateField(
        null=True, blank=True, verbose_name="Baubeginn"
    )
    construction_end = models.DateField(
        null=True, blank=True, verbose_name="Fertigstellung"
    )
    budget_total = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Gesamtbudget (€)",
    )
    cost_estimate = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Kostenschätzung (€)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Erstellt von",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "avb"
        verbose_name = "Bauprojekt"
        verbose_name_plural = "Bauprojekte"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        num = self.project_number or ""
        return f"{num} {self.ifc_project.name}".strip()

    @property
    def total_tender_value(self) -> Decimal:
        return self.tenders.aggregate(
            total=models.Sum("estimated_value")
        )["total"] or Decimal("0")


class ProjectMilestone(models.Model):
    """Projektmeilenstein."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="milestones",
        verbose_name="Projekt",
    )
    name = models.CharField(
        max_length=255, verbose_name="Bezeichnung"
    )
    description = models.TextField(
        blank=True, verbose_name="Beschreibung"
    )
    phase = models.CharField(
        max_length=10,
        choices=ProjectPhase.choices,
        blank=True,
        verbose_name="Leistungsphase",
    )
    due_date = models.DateField(verbose_name="Fällig am")
    completed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Abgeschlossen am",
    )
    order = models.PositiveIntegerField(
        default=0, verbose_name="Reihenfolge"
    )

    class Meta:
        app_label = "avb"
        verbose_name = "Meilenstein"
        verbose_name_plural = "Meilensteine"
        ordering = ["order", "due_date"]

    def __str__(self) -> str:
        return f"{self.name} ({self.due_date})"

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    @property
    def is_overdue(self) -> bool:
        if self.is_completed:
            return False
        return timezone.now().date() > self.due_date


class CostEstimateEntry(models.Model):
    """Kostenschätzung nach DIN 276."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="cost_estimates",
        verbose_name="Projekt",
    )
    cost_group = models.CharField(
        max_length=10,
        choices=CostGroup.choices,
        verbose_name="Kostengruppe",
    )
    description = models.CharField(
        max_length=255, blank=True,
        verbose_name="Beschreibung",
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0"), verbose_name="Menge",
    )
    unit = models.CharField(
        max_length=20, default="m²", verbose_name="Einheit"
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Einheitspreis (€)",
    )
    total = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"), verbose_name="Gesamt (€)",
    )
    notes = models.TextField(
        blank=True, verbose_name="Anmerkungen"
    )

    class Meta:
        app_label = "avb"
        verbose_name = "Kostenschätzung"
        verbose_name_plural = "Kostenschätzungen"
        ordering = ["cost_group"]

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_cost_group_display()} - {self.total:.2f} €"



# Re-export tender/bid models for backward compatibility
from .models_tender import (  # noqa: F401
    Award,
    Bid,
    BidPosition,
    Bidder,
    Tender,
    TenderGroup,
    TenderPosition,
)
