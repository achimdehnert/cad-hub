"""
IFC Component Models

Window, Door, Wall, Slab models.
"""
from django.db import models

from .models import Floor, IFCModel, Room


class Window(models.Model):
    """Fenster (IfcWindow)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_model = models.ForeignKey(
        IFCModel,
        on_delete=models.CASCADE,
        related_name="windows",
        verbose_name="IFC Modell",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="windows",
        verbose_name="Geschoss",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="windows",
        verbose_name="Raum",
    )

    ifc_guid = models.CharField(
        max_length=36, verbose_name="IFC GUID"
    )

    number = models.CharField(
        max_length=50, blank=True, verbose_name="Nummer"
    )
    name = models.CharField(
        max_length=100, blank=True, verbose_name="Name"
    )

    width = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Breite (m)",
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Höhe (m)",
    )
    area = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Fläche (m²)",
    )

    wall_position = models.CharField(
        max_length=50, blank=True, verbose_name="Wandposition"
    )
    elevation = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Höhe (m)",
    )

    material = models.CharField(
        max_length=100, blank=True, verbose_name="Material"
    )
    glazing_type = models.CharField(
        max_length=100, blank=True, verbose_name="Verglasungstyp"
    )
    u_value = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="U-Wert (W/m²K)",
    )

    properties = models.JSONField(
        default=dict, blank=True,
        verbose_name="IFC Properties",
    )

    class Meta:
        app_label = "ifc"
        ordering = ["floor__sort_order", "number"]
        verbose_name = "Fenster"
        verbose_name_plural = "Fenster"

    def __str__(self) -> str:
        return f"{self.number or self.name or self.ifc_guid[:8]}"


class Door(models.Model):
    """Tür (IfcDoor)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_model = models.ForeignKey(
        IFCModel,
        on_delete=models.CASCADE,
        related_name="doors",
        verbose_name="IFC Modell",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors",
        verbose_name="Geschoss",
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors_from",
        verbose_name="Von Raum",
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doors_to",
        verbose_name="Nach Raum",
    )

    ifc_guid = models.CharField(
        max_length=36, verbose_name="IFC GUID"
    )

    number = models.CharField(
        max_length=50, blank=True, verbose_name="Nummer"
    )
    name = models.CharField(
        max_length=100, blank=True, verbose_name="Name"
    )

    width = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Breite (m)",
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Höhe (m)",
    )

    door_type = models.CharField(
        max_length=50, blank=True, verbose_name="Türtyp"
    )
    material = models.CharField(
        max_length=100, blank=True, verbose_name="Material"
    )
    fire_rating = models.CharField(
        max_length=20, blank=True, verbose_name="Feuerwiderstand"
    )

    properties = models.JSONField(
        default=dict, blank=True,
        verbose_name="IFC Properties",
    )

    class Meta:
        app_label = "ifc"
        ordering = ["floor__sort_order", "number"]
        verbose_name = "Tür"
        verbose_name_plural = "Türen"

    def __str__(self) -> str:
        return f"{self.number or self.name or self.ifc_guid[:8]}"


class Wall(models.Model):
    """Wand (IfcWall)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_model = models.ForeignKey(
        IFCModel,
        on_delete=models.CASCADE,
        related_name="walls",
        verbose_name="IFC Modell",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="walls",
        verbose_name="Geschoss",
    )

    ifc_guid = models.CharField(
        max_length=36, verbose_name="IFC GUID"
    )

    name = models.CharField(
        max_length=100, blank=True, verbose_name="Name"
    )

    length = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Länge (m)",
    )
    height = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Höhe (m)",
    )
    width = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Dicke (m)",
    )
    gross_area = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        verbose_name="Bruttofläche (m²)",
    )
    net_area = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        verbose_name="Nettofläche (m²)",
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Volumen (m³)",
    )

    is_external = models.BooleanField(
        default=False, verbose_name="Außenwand"
    )
    is_load_bearing = models.BooleanField(
        default=False, verbose_name="Tragend"
    )
    material = models.CharField(
        max_length=100, blank=True, verbose_name="Material"
    )

    properties = models.JSONField(
        default=dict, blank=True,
        verbose_name="IFC Properties",
    )

    class Meta:
        app_label = "ifc"
        ordering = ["floor__sort_order", "name"]
        verbose_name = "Wand"
        verbose_name_plural = "Wände"

    def __str__(self) -> str:
        wall_type = "Außenwand" if self.is_external else "Innenwand"
        return f"{wall_type} - {self.name or self.ifc_guid[:8]}"


class Slab(models.Model):
    """Decke/Bodenplatte (IfcSlab)."""

    class SlabType(models.TextChoices):
        FLOOR = "FLOOR", "Geschossdecke"
        ROOF = "ROOF", "Dach"
        BASESLAB = "BASESLAB", "Bodenplatte"
        LANDING = "LANDING", "Podest"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tenant_id = models.UUIDField(
        db_index=True, help_text="Multi-tenancy isolator"
    )
    ifc_model = models.ForeignKey(
        IFCModel,
        on_delete=models.CASCADE,
        related_name="slabs",
        verbose_name="IFC Modell",
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slabs",
        verbose_name="Geschoss",
    )

    ifc_guid = models.CharField(
        max_length=36, verbose_name="IFC GUID"
    )

    name = models.CharField(
        max_length=100, blank=True, verbose_name="Name"
    )
    slab_type = models.CharField(
        max_length=20,
        choices=SlabType.choices,
        default=SlabType.FLOOR,
        verbose_name="Typ",
    )

    area = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Fläche (m²)",
    )
    thickness = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Dicke (m)",
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Volumen (m³)",
    )
    perimeter = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True, verbose_name="Umfang (m)",
    )

    material = models.CharField(
        max_length=100, blank=True, verbose_name="Material"
    )

    properties = models.JSONField(
        default=dict, blank=True,
        verbose_name="IFC Properties",
    )

    class Meta:
        app_label = "ifc"
        ordering = ["floor__sort_order", "slab_type", "name"]
        verbose_name = "Decke/Platte"
        verbose_name_plural = "Decken/Platten"

    def __str__(self) -> str:
        return (
            f"{self.get_slab_type_display()}"
            f" - {self.name or self.ifc_guid[:8]}"
        )
