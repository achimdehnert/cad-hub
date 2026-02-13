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


class Tender(models.Model):
    """Ausschreibung / Leistungsverzeichnis."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="tenders",
        verbose_name="Projekt",
    )
    tender_number = models.CharField(
        max_length=50, verbose_name="Ausschreibungsnummer"
    )
    title = models.CharField(
        max_length=255, verbose_name="Titel"
    )
    description = models.TextField(
        blank=True, verbose_name="Beschreibung"
    )
    cost_group = models.CharField(
        max_length=10,
        choices=CostGroup.choices,
        blank=True, verbose_name="Kostengruppe",
    )
    trade = models.CharField(
        max_length=100, blank=True, verbose_name="Gewerk"
    )
    status = models.CharField(
        max_length=20,
        choices=TenderStatus.choices,
        default=TenderStatus.DRAFT,
        verbose_name="Status",
    )
    publication_date = models.DateField(
        null=True, blank=True,
        verbose_name="Veröffentlichung",
    )
    submission_deadline = models.DateTimeField(
        null=True, blank=True, verbose_name="Abgabefrist"
    )
    opening_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Eröffnungstermin",
    )
    estimated_value = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Schätzwert (€)",
    )
    gaeb_file = models.FileField(
        upload_to="tenders/gaeb/%Y/%m/",
        blank=True, verbose_name="GAEB X81 Datei",
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
        verbose_name = "Ausschreibung"
        verbose_name_plural = "Ausschreibungen"
        ordering = ["-created_at"]
        unique_together = ["project", "tender_number"]

    def __str__(self) -> str:
        return f"{self.tender_number} - {self.title}"

    @property
    def positions_count(self) -> int:
        return self.positions.count()

    @property
    def bids_count(self) -> int:
        return self.bids.count()

    @property
    def lowest_bid(self):
        return self.bids.filter(
            status__in=[
                BidStatus.RECEIVED, BidStatus.EVALUATED,
            ]
        ).order_by("total_price").first()


class TenderPosition(models.Model):
    """LV-Position in einer Ausschreibung."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Ausschreibung",
    )
    oz = models.CharField(max_length=20, verbose_name="OZ")
    short_text = models.CharField(
        max_length=255, verbose_name="Kurztext"
    )
    long_text = models.TextField(
        blank=True, verbose_name="Langtext"
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3,
        default=Decimal("0"), verbose_name="Menge",
    )
    unit = models.CharField(
        max_length=20, default="Stk", verbose_name="Einheit"
    )
    stlb_code = models.CharField(
        max_length=20, blank=True, verbose_name="STLB-Code"
    )
    ifc_element_guids = models.JSONField(
        default=list, blank=True,
        verbose_name="IFC Element GUIDs",
    )
    order = models.PositiveIntegerField(
        default=0, verbose_name="Reihenfolge"
    )

    class Meta:
        app_label = "avb"
        verbose_name = "LV-Position"
        verbose_name_plural = "LV-Positionen"
        ordering = ["order", "oz"]

    def __str__(self) -> str:
        return f"{self.oz} - {self.short_text}"


class TenderGroup(models.Model):
    """Los/Titel/Gruppe im LV."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="groups",
        verbose_name="Ausschreibung",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="children",
        verbose_name="Übergeordnete Gruppe",
    )
    oz = models.CharField(max_length=20, verbose_name="OZ")
    title = models.CharField(
        max_length=255, verbose_name="Titel"
    )
    description = models.TextField(
        blank=True, verbose_name="Beschreibung"
    )
    order = models.PositiveIntegerField(
        default=0, verbose_name="Reihenfolge"
    )

    class Meta:
        app_label = "avb"
        verbose_name = "LV-Gruppe"
        verbose_name_plural = "LV-Gruppen"
        ordering = ["order", "oz"]

    def __str__(self) -> str:
        return f"{self.oz} - {self.title}"


class Bidder(models.Model):
    """Bieter / Unternehmen."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    company_name = models.CharField(
        max_length=255, verbose_name="Firmenname"
    )
    contact_person = models.CharField(
        max_length=255, blank=True,
        verbose_name="Ansprechpartner",
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
    country = models.CharField(
        max_length=100, default="Deutschland",
        verbose_name="Land",
    )
    email = models.EmailField(
        blank=True, verbose_name="E-Mail"
    )
    phone = models.CharField(
        max_length=50, blank=True, verbose_name="Telefon"
    )
    website = models.URLField(
        blank=True, verbose_name="Website"
    )
    trades = models.JSONField(
        default=list, blank=True, verbose_name="Gewerke"
    )
    certifications = models.JSONField(
        default=list, blank=True,
        verbose_name="Zertifizierungen",
    )
    rating = models.DecimalField(
        max_digits=3, decimal_places=1,
        null=True, blank=True,
        verbose_name="Bewertung (1-5)",
    )
    notes = models.TextField(
        blank=True, verbose_name="Notizen"
    )
    is_active = models.BooleanField(
        default=True, verbose_name="Aktiv"
    )
    is_preferred = models.BooleanField(
        default=False, verbose_name="Bevorzugter Bieter"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "avb"
        verbose_name = "Bieter"
        verbose_name_plural = "Bieter"
        ordering = ["company_name"]

    def __str__(self) -> str:
        return self.company_name


class Bid(models.Model):
    """Angebot eines Bieters."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="bids",
        verbose_name="Ausschreibung",
    )
    bidder = models.ForeignKey(
        Bidder,
        on_delete=models.CASCADE,
        related_name="bids",
        verbose_name="Bieter",
    )
    status = models.CharField(
        max_length=20,
        choices=BidStatus.choices,
        default=BidStatus.INVITED,
        verbose_name="Status",
    )
    invited_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Eingeladen am"
    )
    received_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Eingegangen am"
    )
    total_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Angebotssumme netto (€)",
    )
    total_price_gross = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Angebotssumme brutto (€)",
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal("0"), verbose_name="Nachlass (%)",
    )
    discount_absolute = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0"), verbose_name="Nachlass (€)",
    )
    valid_until = models.DateField(
        null=True, blank=True, verbose_name="Gültig bis"
    )
    gaeb_file = models.FileField(
        upload_to="bids/gaeb/%Y/%m/",
        blank=True, verbose_name="GAEB X83 Datei",
    )
    technical_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Technische Bewertung",
    )
    price_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Preis-Bewertung",
    )
    total_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Gesamtbewertung",
    )
    notes = models.TextField(
        blank=True, verbose_name="Anmerkungen"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "avb"
        verbose_name = "Angebot"
        verbose_name_plural = "Angebote"
        ordering = ["total_price"]
        unique_together = ["tender", "bidder"]

    def __str__(self) -> str:
        name = self.bidder.company_name
        return f"{name} - {self.total_price:.2f} €"

    @property
    def final_price(self) -> Decimal:
        price = self.total_price
        if self.discount_percent > 0:
            price -= price * (self.discount_percent / 100)
        price -= self.discount_absolute
        return price

    @property
    def rank(self) -> int:
        lower = self.tender.bids.filter(
            total_price__lt=self.total_price,
            status__in=[
                BidStatus.RECEIVED, BidStatus.EVALUATED,
            ],
        ).count()
        return lower + 1


class BidPosition(models.Model):
    """Einzelposition im Angebot."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    bid = models.ForeignKey(
        Bid,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Angebot",
    )
    tender_position = models.ForeignKey(
        TenderPosition,
        on_delete=models.CASCADE,
        related_name="bid_positions",
        verbose_name="LV-Position",
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Einheitspreis (€)",
    )
    total_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=Decimal("0"),
        verbose_name="Gesamtpreis (€)",
    )
    quantity_correction = models.DecimalField(
        max_digits=12, decimal_places=3,
        null=True, blank=True,
        verbose_name="Mengenkorrektur",
    )
    notes = models.TextField(
        blank=True, verbose_name="Anmerkungen"
    )

    class Meta:
        app_label = "avb"
        verbose_name = "Angebotsposition"
        verbose_name_plural = "Angebotspositionen"
        ordering = ["tender_position__order"]

    def save(self, *args, **kwargs):
        qty = (
            self.quantity_correction
            or self.tender_position.quantity
        )
        self.total_price = qty * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        oz = self.tender_position.oz
        return f"{oz} - {self.unit_price:.2f} €"


class Award(models.Model):
    """Zuschlag / Vergabe."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    tender = models.OneToOneField(
        Tender,
        on_delete=models.CASCADE,
        related_name="award",
        verbose_name="Ausschreibung",
    )
    bid = models.OneToOneField(
        Bid,
        on_delete=models.CASCADE,
        related_name="award",
        verbose_name="Angebot",
    )
    award_date = models.DateField(
        verbose_name="Zuschlagsdatum"
    )
    contract_value = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name="Auftragssumme (€)",
    )
    contract_number = models.CharField(
        max_length=50, blank=True,
        verbose_name="Vertragsnummer",
    )
    contract_file = models.FileField(
        upload_to="awards/contracts/%Y/%m/",
        blank=True, verbose_name="Vertragsdatei",
    )
    gaeb_file = models.FileField(
        upload_to="awards/gaeb/%Y/%m/",
        blank=True, verbose_name="GAEB X85 Datei",
    )
    notes = models.TextField(
        blank=True, verbose_name="Anmerkungen"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Erstellt von",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "avb"
        verbose_name = "Vergabe"
        verbose_name_plural = "Vergaben"
        ordering = ["-award_date"]

    def __str__(self) -> str:
        title = self.tender.title
        company = self.bid.bidder.company_name
        return f"Vergabe: {title} an {company}"
