"""
Brandschutz models — symbols, inspections, defects, proposals, regulations.

Source: bfagent/apps/cad_hub/models/brandschutz.py
Changes: app_label → brandschutz, tenant_id added.
"""
import uuid

from django.db import models
from django.utils import timezone


class BrandschutzKategorie(models.TextChoices):
    FLUCHTWEG = "fluchtweg", "Fluchtweg"
    NOTAUSGANG = "notausgang", "Notausgang"
    BRANDABSCHNITT = "brandabschnitt", "Brandabschnitt"
    FEUERLOESCHER = "feuerloescher", "Feuerlöscher"
    RAUCHMELDER = "rauchmelder", "Rauchmelder"
    SPRINKLER = "sprinkler", "Sprinkler"
    RWA = "rwa", "RWA"
    EX_ZONE = "ex_zone", "Ex-Zone"
    BRANDMELDER = "brandmelder", "Brandmelder"
    HYDRANT = "hydrant", "Hydrant"


class Feuerwiderstandsklasse(models.TextChoices):
    F30 = "F30", "F30 (30 min)"
    F60 = "F60", "F60 (60 min)"
    F90 = "F90", "F90 (90 min)"
    F120 = "F120", "F120 (120 min)"
    F180 = "F180", "F180 (180 min)"


class ExZoneTyp(models.TextChoices):
    ZONE_0 = "zone_0", "Zone 0 (Gas, ständig)"
    ZONE_1 = "zone_1", "Zone 1 (Gas, gelegentlich)"
    ZONE_2 = "zone_2", "Zone 2 (Gas, selten)"
    ZONE_20 = "zone_20", "Zone 20 (Staub, ständig)"
    ZONE_21 = "zone_21", "Zone 21 (Staub, gelegentlich)"
    ZONE_22 = "zone_22", "Zone 22 (Staub, selten)"


class PruefStatus(models.TextChoices):
    ENTWURF = "entwurf", "Entwurf"
    IN_PRUEFUNG = "in_pruefung", "In Prüfung"
    ABGESCHLOSSEN = "abgeschlossen", "Abgeschlossen"
    MAENGEL = "maengel", "Mängel festgestellt"
    FREIGEGEBEN = "freigegeben", "Freigegeben"


class BrandschutzSymbol(models.Model):
    """Brandschutz-Symbol nach DIN EN ISO 7010."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    name = models.CharField(max_length=100)
    din_nummer = models.CharField(max_length=20)
    kategorie = models.CharField(
        max_length=50,
        choices=BrandschutzKategorie.choices,
        default=BrandschutzKategorie.FEUERLOESCHER,
    )
    beschreibung = models.TextField(blank=True)
    block_dxf = models.FileField(
        upload_to="brandschutz/symbole/",
        blank=True, null=True,
    )
    block_json = models.JSONField(blank=True, null=True)
    farbe = models.CharField(max_length=20, default="rot")
    groesse_mm = models.FloatField(default=200)
    regelwerk = models.CharField(max_length=100, blank=True)
    aktiv = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "brandschutz"
        verbose_name = "Brandschutz-Symbol"
        verbose_name_plural = "Brandschutz-Symbole"
        ordering = ["kategorie", "din_nummer"]

    def __str__(self) -> str:
        return f"{self.din_nummer} - {self.name}"


class BrandschutzPruefung(models.Model):
    """Brandschutz-Prüfung für ein Projekt/Plan."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    titel = models.CharField(max_length=200)
    projekt_name = models.CharField(max_length=200)
    projekt_id = models.UUIDField(blank=True, null=True)
    gebaeude_typ = models.CharField(max_length=50, blank=True)
    etage = models.CharField(
        max_length=50, blank=True, default="EG"
    )
    flaeche_qm = models.FloatField(blank=True, null=True)
    beschreibung = models.TextField(blank=True)
    quelldatei = models.FileField(
        upload_to="brandschutz/plaene/",
        blank=True, null=True,
    )
    report_pdf = models.FileField(
        upload_to="brandschutz/reports/",
        blank=True, null=True,
    )
    status = models.CharField(
        max_length=50,
        choices=PruefStatus.choices,
        default=PruefStatus.ENTWURF,
    )
    analyse_ergebnis = models.JSONField(
        blank=True, null=True
    )
    pruefer = models.CharField(max_length=200, blank=True)
    pruef_datum = models.DateField(blank=True, null=True)
    naechste_pruefung = models.DateField(
        blank=True, null=True
    )
    erstellt_am = models.DateTimeField(auto_now_add=True)
    aktualisiert_am = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "brandschutz"
        verbose_name = "Brandschutz-Prüfung"
        verbose_name_plural = "Brandschutz-Prüfungen"
        ordering = ["-pruef_datum", "-erstellt_am"]

    def __str__(self) -> str:
        return f"{self.titel} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.titel:
            self.titel = f"Prüfung {self.projekt_name}"
        if not self.pruef_datum:
            self.pruef_datum = timezone.now().date()
        super().save(*args, **kwargs)


class BrandschutzMangel(models.Model):
    """Einzelner Mangel aus einer Brandschutz-Prüfung."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    pruefung = models.ForeignKey(
        BrandschutzPruefung,
        on_delete=models.CASCADE,
        related_name="maengel",
    )
    kategorie = models.CharField(
        max_length=50,
        choices=BrandschutzKategorie.choices,
        default=BrandschutzKategorie.FLUCHTWEG,
    )
    beschreibung = models.TextField()
    schweregrad = models.CharField(
        max_length=20,
        choices=[
            ("kritisch", "Kritisch"),
            ("hoch", "Hoch"),
            ("mittel", "Mittel"),
            ("gering", "Gering"),
        ],
        default="mittel",
    )
    regelwerk_referenz = models.CharField(
        max_length=100, blank=True,
    )
    position_x = models.FloatField(blank=True, null=True)
    position_y = models.FloatField(blank=True, null=True)
    behoben = models.BooleanField(default=False)
    behoben_am = models.DateTimeField(blank=True, null=True)
    behoben_kommentar = models.TextField(blank=True)
    foto = models.ImageField(
        upload_to="brandschutz/maengel/",
        blank=True, null=True,
    )
    notizen = models.TextField(blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    aktualisiert_am = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "brandschutz"
        verbose_name = "Brandschutz-Mangel"
        verbose_name_plural = "Brandschutz-Mängel"
        ordering = ["-schweregrad", "-erstellt_am"]

    def __str__(self) -> str:
        desc = self.beschreibung[:50]
        return f"{self.get_kategorie_display()}: {desc}"


class BrandschutzSymbolVorschlag(models.Model):
    """Vorgeschlagenes Symbol für eine Prüfung."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    pruefung = models.ForeignKey(
        BrandschutzPruefung,
        on_delete=models.CASCADE,
        related_name="symbole",
    )
    symbol_typ = models.CharField(max_length=50)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    raum_referenz = models.CharField(
        max_length=100, blank=True
    )
    begruendung = models.TextField(blank=True)
    regelwerk_basis = models.CharField(
        max_length=100, blank=True
    )
    prioritaet = models.IntegerField(default=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ("vorgeschlagen", "Vorgeschlagen"),
            ("genehmigt", "Genehmigt"),
            ("abgelehnt", "Abgelehnt"),
            ("eingefuegt", "Eingefügt"),
        ],
        default="vorgeschlagen",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "brandschutz"
        verbose_name = "Symbol-Vorschlag"
        verbose_name_plural = "Symbol-Vorschläge"
        ordering = ["prioritaet", "-erstellt_am"]

    def __str__(self) -> str:
        x, y = self.position_x, self.position_y
        return f"{self.symbol_typ} @ ({x:.0f}, {y:.0f})"


class BrandschutzRegelwerk(models.Model):
    """Regelwerk-Referenz für Brandschutz-Prüfungen."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    kuerzel = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    TYP_CHOICES = [
        ("asr", "Arbeitsstättenregel"),
        ("din", "DIN-Norm"),
        ("lbo", "Landesbauordnung"),
        ("mbo", "Musterbauordnung"),
        ("vstaettvo", "Versammlungsstättenverordnung"),
        ("indbauril", "Industriebaurichtlinie"),
        ("sonstige", "Sonstige"),
    ]
    typ = models.CharField(
        max_length=20, choices=TYP_CHOICES, default="din"
    )
    kategorien = models.JSONField(default=list)
    regeln = models.JSONField(default=dict)
    url = models.URLField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    gueltig_ab = models.DateField(blank=True, null=True)
    aktiv = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "brandschutz"
        verbose_name = "Brandschutz-Regelwerk"
        verbose_name_plural = "Brandschutz-Regelwerke"
        ordering = ["typ", "kuerzel"]

    def __str__(self) -> str:
        return f"{self.kuerzel} - {self.name}"
