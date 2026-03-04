"""
Registry models — Modul-Katalog, Berufsprofile, Tenant-Subscriptions.

DB-Master für alle nl2cad-Module, Berufsprofile, Preise und Subscriptions.
Seed via: python manage.py import_registry_seed
API: GET /api/registry/modules/?product=nl2cad
"""
import uuid
from decimal import Decimal

from django.db import models

from apps.core.managers import TenantAwareManager


# ─────────────────────────────────────────────────────────────────────────────
# MODUL-KATALOG (platform-global, kein tenant_id)
# ─────────────────────────────────────────────────────────────────────────────

class ModuleStatus(models.TextChoices):
    STABLE     = "stable",     "Stabil (produktiv)"
    BETA       = "beta",       "Beta"
    PLANNED    = "planned",    "In Planung"
    DEPRECATED = "deprecated", "Veraltet"


class ModulePriority(models.TextChoices):
    HIGH   = "high",   "Hoch"
    MEDIUM = "medium", "Mittel"
    LOW    = "low",    "Niedrig"


class NL2CADModule(models.Model):
    """
    Ein buchbares nl2cad-Package.

    Platform-global (kein Tenant-Bezug) — wird per Django Admin gepflegt.
    Seed: management/commands/import_registry_seed.py
    """

    id          = models.SlugField(
        primary_key=True,
        help_text="URL-sicherer Bezeichner, z.B. 'brandschutz'",
    )
    package     = models.CharField(
        max_length=120, unique=True,
        verbose_name="PyPI-Package-Name",
        help_text="z.B. 'nl2cad-brandschutz'",
    )
    name        = models.CharField(max_length=120, verbose_name="Anzeigename")
    icon        = models.CharField(max_length=10, default="📦", verbose_name="Icon (Emoji)")
    color       = models.CharField(max_length=7, default="#2563eb", verbose_name="Farbe (Hex)")
    tagline     = models.CharField(max_length=200, blank=True, verbose_name="Kurzzeile")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    features    = models.JSONField(
        default=list,
        verbose_name="Features",
        help_text="Liste von Feature-Strings, z.B. ['DIN 277', 'WoFlV']",
    )
    deps        = models.JSONField(
        default=list,
        verbose_name="Abhängigkeiten",
        help_text="Liste von Package-IDs, z.B. ['nl2cad-core']",
    )
    norms       = models.JSONField(
        default=list,
        verbose_name="Regelwerke / Normen",
        help_text="z.B. ['DIN 277 (2016)', 'WoFlV 2004']",
    )
    main_classes = models.JSONField(
        default=list,
        verbose_name="Wichtigste Klassen",
        help_text="z.B. ['DIN277Calculator', 'WoFlVCalculator']",
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name="Pflicht (immer aktiv)",
        help_text="True für nl2cad-core — kann nicht abgewählt werden",
    )
    status      = models.CharField(
        max_length=20,
        choices=ModuleStatus.choices,
        default=ModuleStatus.PLANNED,
        verbose_name="Status",
        db_index=True,
    )
    priority    = models.CharField(
        max_length=10,
        choices=ModulePriority.choices,
        default=ModulePriority.MEDIUM,
        verbose_name="Priorität",
    )
    story_points = models.PositiveIntegerField(
        default=0,
        verbose_name="Story Points",
    )
    target_quarter = models.CharField(
        max_length=20, blank=True,
        verbose_name="Ziel-Quartal",
        help_text="z.B. 'Q2/2026'",
    )
    adr_path    = models.CharField(
        max_length=255, blank=True,
        verbose_name="ADR-Pfad",
        help_text="Relativ zum Repo-Root, z.B. 'docs/adr/ADR-001-...'",
    )
    workflow_path = models.CharField(
        max_length=255, blank=True,
        verbose_name="Workflow-Pfad",
    )
    pypi_url    = models.URLField(blank=True, verbose_name="PyPI-URL")
    sort_order  = models.PositiveIntegerField(default=0, verbose_name="Reihenfolge")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "registry"
        verbose_name = "nl2cad-Modul"
        verbose_name_plural = "nl2cad-Module"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.package} ({self.get_status_display()})"

    @property
    def standard_pricing(self) -> "ModulePricing | None":
        return self.pricing_tiers.filter(organization__isnull=True).first()


class ModulePricing(models.Model):
    """
    Preismodell für ein Modul.

    organization=None  → Standard-Preis (global)
    organization=X     → Individueller Preis für Tenant X (Custom Pricing)
    """

    class PricingType(models.TextChoices):
        STANDARD = "standard", "Standard"
        CUSTOM   = "custom",   "Individuell (Tenant-spezifisch)"
        FREE     = "free",     "Kostenlos"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module       = models.ForeignKey(
        NL2CADModule,
        on_delete=models.CASCADE,
        related_name="pricing_tiers",
        verbose_name="Modul",
    )
    organization = models.ForeignKey(
        "django_tenancy.Organization",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="custom_module_pricing",
        verbose_name="Organisation (leer = Standard)",
    )
    pricing_type = models.CharField(
        max_length=20,
        choices=PricingType.choices,
        default=PricingType.STANDARD,
        verbose_name="Preistyp",
    )
    setup_eur    = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0"),
        verbose_name="Setup-Preis (€)",
    )
    monthly_eur  = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0"),
        verbose_name="Monatspreis (€)",
    )
    label        = models.CharField(
        max_length=100, blank=True,
        verbose_name="Preis-Label",
        help_text="z.B. '79 € / Monat'",
    )
    valid_from   = models.DateField(null=True, blank=True, verbose_name="Gültig ab")
    valid_until  = models.DateField(null=True, blank=True, verbose_name="Gültig bis")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "registry"
        verbose_name = "Modul-Preis"
        verbose_name_plural = "Modul-Preise"
        unique_together = [("module", "organization")]
        ordering = ["module", "organization"]
        indexes = [
            models.Index(fields=["module", "organization"]),
        ]

    def __str__(self) -> str:
        org = f" [{self.organization}]" if self.organization_id else " [Standard]"
        return f"{self.module_id}{org}: {self.monthly_eur} €/Monat"

    def save(self, *args, **kwargs) -> None:
        if not self.label:
            if self.monthly_eur == 0 and self.setup_eur == 0:
                self.label = "Inklusive (Basis)"
            elif self.setup_eur > 0:
                self.label = f"{self.setup_eur:.0f} € Setup + {self.monthly_eur:.0f} € / Monat"
            else:
                self.label = f"{self.monthly_eur:.0f} € / Monat"
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# BERUFSPROFILE
# ─────────────────────────────────────────────────────────────────────────────

class BerufsProfil(models.Model):
    """
    Berufstypisches Konfigurationsprofil für nl2cad.

    Definiert welche Module, NLP-Keywords und Report-Templates
    für eine Berufsgruppe typisch sind.
    Wird im Konfigurator als Vorauswahl angeboten.
    """

    id              = models.SlugField(
        primary_key=True,
        help_text="z.B. 'brandschutz_sv', 'architekt'",
    )
    name            = models.CharField(max_length=100, verbose_name="Berufsbezeichnung")
    icon            = models.CharField(max_length=10, default="👤", verbose_name="Icon")
    fokus           = models.CharField(
        max_length=200, blank=True,
        verbose_name="Fachlicher Fokus",
        help_text="z.B. 'Fluchtweg-Prüfung, Brandschutzkonzept'",
    )
    bereitschaft    = models.CharField(
        max_length=100, blank=True,
        verbose_name="Sofort-Bereitschaft",
        help_text="z.B. '85% sofort'",
    )
    modules         = models.ManyToManyField(
        NL2CADModule,
        through="ProfilModuleMapping",
        related_name="berufsprofile",
        verbose_name="Module",
    )
    install_command = models.TextField(
        blank=True,
        verbose_name="pip install Befehl",
    )
    yaml_config     = models.TextField(
        blank=True,
        verbose_name="YAML-Konfiguration",
        help_text="Fertiges YAML für dieses Berufsprofil",
    )
    nlp_keywords    = models.TextField(
        blank=True,
        verbose_name="NLP-Keywords",
        help_text="Komma-getrennte Keywords für Intent-Klassifikation",
    )
    report_template = models.CharField(
        max_length=100, blank=True,
        verbose_name="Report-Template",
        help_text="z.B. 'brandschutz_gutachten.jinja2'",
    )
    primary_output  = models.CharField(
        max_length=200, blank=True,
        verbose_name="Primärer Output",
        help_text="z.B. 'Brandschutz-Gutachten (PDF), Mängelprotokoll'",
    )
    sort_order      = models.PositiveIntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "registry"
        verbose_name = "Berufsprofil"
        verbose_name_plural = "Berufsprofile"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return f"{self.icon} {self.name}"

    @property
    def nlp_keywords_list(self) -> list[str]:
        return [kw.strip() for kw in self.nlp_keywords.split(",") if kw.strip()]


class ProfilModuleMapping(models.Model):
    """
    Zwischentabelle: Berufsprofil ↔ Modul mit Mapping-Typ.

    mapping_type unterscheidet ob das Modul bereits vorhanden,
    nur Konfiguration nötig oder Neu-Entwicklung ist.
    """

    class MappingType(models.TextChoices):
        VORHANDEN        = "vorhanden",    "✅ Vorhanden"
        KONFIGURATION    = "konfiguration","🔧 Nur Konfiguration nötig"
        NEU_ENTWICKLUNG  = "neu",          "🔨 Neu-Entwicklung"
        NICHT_RELEVANT   = "nicht",        "— Nicht relevant"

    profil       = models.ForeignKey(BerufsProfil, on_delete=models.CASCADE)
    module       = models.ForeignKey(NL2CADModule, on_delete=models.CASCADE)
    mapping_type = models.CharField(
        max_length=20,
        choices=MappingType.choices,
        default=MappingType.NEU_ENTWICKLUNG,
        verbose_name="Mapping-Typ",
    )
    is_recommended = models.BooleanField(
        default=True,
        verbose_name="Empfohlen",
        help_text="Wird im Konfigurator vorausgewählt",
    )

    class Meta:
        app_label = "registry"
        verbose_name = "Profil-Modul-Zuordnung"
        verbose_name_plural = "Profil-Modul-Zuordnungen"
        unique_together = [("profil", "module")]
        ordering = ["profil", "module__sort_order"]

    def __str__(self) -> str:
        return f"{self.profil_id} → {self.module_id} ({self.get_mapping_type_display()})"


# ─────────────────────────────────────────────────────────────────────────────
# TENANT-SUBSCRIPTIONS
# ─────────────────────────────────────────────────────────────────────────────

class TenantSubscription(models.Model):
    """
    Aktive Modul-Subscription einer Organisation (Tenant).

    Entsteht nach Freigabe via GitHub Actions Workflow (tenant-onboarding.yml).
    Wird per Django Admin verwaltet (aktivieren, deaktivieren, Preis anpassen).
    """

    objects = TenantAwareManager()

    class SubscriptionStatus(models.TextChoices):
        PENDING    = "pending",    "Ausstehend (Freigabe erwartet)"
        TRIAL      = "trial",      "Test-Phase"
        ACTIVE     = "active",     "Aktiv"
        SUSPENDED  = "suspended",  "Gesperrt"
        CANCELLED  = "cancelled",  "Gekündigt"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id    = models.UUIDField(db_index=True, help_text="Multi-tenancy isolator")
    organization = models.ForeignKey(
        "django_tenancy.Organization",
        on_delete=models.CASCADE,
        related_name="module_subscriptions",
        verbose_name="Organisation",
    )
    module       = models.ForeignKey(
        NL2CADModule,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name="Modul",
    )
    berufsprofil = models.ForeignKey(
        BerufsProfil,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Berufsprofil (bei Onboarding gewählt)",
    )
    status       = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
        verbose_name="Status",
        db_index=True,
    )
    monthly_eur  = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0"),
        verbose_name="Aktueller Monatspreis (€)",
        help_text="Kann vom Standard-Preis abweichen (Custom Pricing)",
    )
    setup_eur    = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0"),
        verbose_name="Setup-Preis (€)",
    )
    activated_at  = models.DateTimeField(null=True, blank=True, verbose_name="Aktiviert am")
    cancelled_at  = models.DateTimeField(null=True, blank=True, verbose_name="Gekündigt am")
    trial_until   = models.DateField(null=True, blank=True, verbose_name="Test-Phase bis")
    approved_by   = models.CharField(max_length=100, blank=True, verbose_name="Freigabe durch")
    notes         = models.TextField(blank=True, verbose_name="Interne Notizen")
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "registry"
        verbose_name = "Modul-Subscription"
        verbose_name_plural = "Modul-Subscriptions"
        unique_together = [("organization", "module")]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.organization} → {self.module_id} ({self.get_status_display()})"

    @property
    def monthly_revenue(self) -> Decimal:
        if self.status == self.SubscriptionStatus.ACTIVE:
            return self.monthly_eur
        return Decimal("0")


class DiscountRule(models.Model):
    """Rabatt-Regeln für das nl2cad-Modul-Bundle (z.B. 15% ab 3 Modulen)."""

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name             = models.CharField(max_length=100, verbose_name="Bezeichnung")
    min_modules      = models.PositiveIntegerField(
        default=3, verbose_name="Mind. Anzahl Module",
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("15"),
        verbose_name="Rabatt (%)",
    )
    is_active        = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "registry"
        verbose_name = "Rabatt-Regel"
        verbose_name_plural = "Rabatt-Regeln"
        ordering = ["min_modules"]

    def __str__(self) -> str:
        return f"{self.discount_percent}% ab {self.min_modules} Modulen"
