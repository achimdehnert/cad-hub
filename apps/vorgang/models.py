"""Vorgang models — Vorgang, Dokument, Befund (Issue #72 K4, #77).

Gemeinsames Vorgangsmodell für Sachbearbeitung UND Einreicher: die Rolle
(``eingereicht_von_rolle``) und eine Löschfrist je Vorgang (``loeschfrist_am``)
sind ab dem ersten Wurf Teil des Modells — Owner-Go 2026-09-23 (#77), damit
die Vorprüfung vor Einreichung (#77, gesperrt bis Kill-Gate KONZ-meiki-010)
später ohne Umbau des Datenmodells aufsetzen kann. Gebaut wird hier nur #72
K4 (Sachbearbeitung); #77 selbst bleibt ungebaut.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.core.managers import TenantAwareManager


def dokument_upload_pfad(instance: "Dokument", dateiname: str) -> str:
    """``vorgang/<tenant_id>/<vorgang_id>/<dateiname>`` — pro Vorgang isoliert."""
    return f"vorgang/{instance.tenant_id}/{instance.vorgang_id}/{dateiname}"


class VorgangArt(models.TextChoices):
    BAUANTRAG = "bauantrag", "Bauantrag"
    AUSSCHREIBUNG = "ausschreibung", "Ausschreibung"


class VorgangRolle(models.TextChoices):
    SACHBEARBEITUNG = "sachbearbeitung", "Sachbearbeitung"
    EINREICHER = "einreicher", "Einreicher"


class VorgangStatus(models.TextChoices):
    OFFEN = "offen", "Offen"
    GEPRUEFT = "geprueft", "Geprüft"
    GESCHLOSSEN = "geschlossen", "Geschlossen"


class VorlagenArt(models.TextChoices):
    LAGEPLAN = "lageplan", "Lageplan"
    GRUNDRISS = "grundriss", "Grundriss"
    SCHNITT = "schnitt", "Schnitt"
    ANSICHT = "ansicht", "Ansicht"
    BAUBESCHREIBUNG = "baubeschreibung", "Baubeschreibung"
    BERECHNUNG = "berechnung", "Berechnung"
    NACHWEIS = "nachweis", "Nachweis"
    FORMULAR = "formular", "Formular"
    UNBEKANNT = "unbekannt", "Unbekannt"


class BefundStatus(models.TextChoices):
    OFFEN = "offen", "Offen"
    BESTAETIGT = "bestaetigt", "Bestätigt"
    VERWORFEN = "verworfen", "Verworfen"


class Vorgang(models.Model):
    """Ein Vorgang (Bauantrag oder Ausschreibung) — Container für Dokumente + Befunde."""

    objects = TenantAwareManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, help_text="Multi-tenancy isolator")

    art = models.CharField(max_length=20, choices=VorgangArt.choices)
    titel = models.CharField(max_length=200)
    eingereicht_von_rolle = models.CharField(
        max_length=20,
        choices=VorgangRolle.choices,
        default=VorgangRolle.SACHBEARBEITUNG,
        verbose_name="Rolle",
    )
    status = models.CharField(
        max_length=20, choices=VorgangStatus.choices, default=VorgangStatus.OFFEN
    )
    loeschfrist_am = models.DateField(
        null=True,
        blank=True,
        verbose_name="Löschfrist",
        help_text=(
            "Pflicht bei Rolle 'einreicher' (#77) — wird im Service "
            "(lege_vorgang_an) erzwungen, nicht per DB-Constraint."
        ),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant_id", "created_at"])]
        verbose_name = "Vorgang"
        verbose_name_plural = "Vorgänge"

    def __str__(self) -> str:
        return f"{self.get_art_display()}: {self.titel}"


class Dokument(models.Model):
    """Ein hochgeladenes Dokument innerhalb eines Vorgangs."""

    objects = TenantAwareManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, help_text="Multi-tenancy isolator")

    vorgang = models.ForeignKey(Vorgang, on_delete=models.CASCADE, related_name="dokumente")
    datei = models.FileField(upload_to=dokument_upload_pfad)
    dateiname = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, db_index=True)
    vorlagenart = models.CharField(
        max_length=20, choices=VorlagenArt.choices, default=VorlagenArt.UNBEKANNT
    )
    seiten = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant_id", "created_at"])]
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"

    def __str__(self) -> str:
        return self.dateiname


class Befund(models.Model):
    """Ein Prüf-Befund zu einem Dokument innerhalb eines Vorgangs."""

    objects = TenantAwareManager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True, help_text="Multi-tenancy isolator")

    vorgang = models.ForeignKey(Vorgang, on_delete=models.CASCADE, related_name="befunde")
    dokument = models.ForeignKey(
        Dokument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="befunde",
    )
    regel_id = models.CharField(max_length=100, help_text="z. B. 'lageplan.massstab'")
    feld = models.CharField(max_length=100, blank=True)
    wert = models.TextField(blank=True)
    konfidenz = models.FloatField(null=True, blank=True)
    seite = models.PositiveIntegerField(null=True, blank=True)
    quelle = models.JSONField(
        default=dict, blank=True, help_text="Fundort (Box/Textstelle), falls geliefert"
    )
    status = models.CharField(
        max_length=20, choices=BefundStatus.choices, default=BefundStatus.OFFEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant_id", "created_at"])]
        verbose_name = "Befund"
        verbose_name_plural = "Befunde"

    def __str__(self) -> str:
        return f"{self.regel_id} ({self.status})"
