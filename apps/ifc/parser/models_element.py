"""
IFC Parser Element Models

ParsedElement, ParsedElementType, ParsedProject dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .models import (
    IfcSchemaVersion,
    ParsedBuilding,
    ParsedClassification,
    ParsedMaterial,
    ParsedProperty,
    ParsedQuantity,
    ParsedSite,
    ParsedSpace,
    ParsedStorey,
)


class ParsedElement:
    """Allgemeines IFC Bauelement mit allen Properties."""

    global_id: str
    ifc_class: str  # z.B. "IfcWall", "IfcDoor"
    name: str | None = None
    description: str | None = None
    object_type: str | None = None  # Typ-Bezeichnung
    tag: str | None = None  # Kennzeichnung/Tag

    # Referenzen
    storey_global_id: str | None = None
    type_global_id: str | None = None
    host_element_id: str | None = None  # z.B. Wand bei Tür

    # Position
    position_x: Decimal | None = None
    position_y: Decimal | None = None
    position_z: Decimal | None = None

    # Geometrie - abgeleitet aus Quantities
    length_m: Decimal | None = None
    width_m: Decimal | None = None
    height_m: Decimal | None = None
    thickness_m: Decimal | None = None
    area_m2: Decimal | None = None
    volume_m3: Decimal | None = None
    gross_area_m2: Decimal | None = None
    net_area_m2: Decimal | None = None
    opening_area_m2: Decimal | None = None  # Fläche der Öffnungen

    # Wichtige Flags
    is_external: bool | None = None  # Außenbauteil
    is_load_bearing: bool | None = None  # Tragend

    # Brandschutz
    fire_rating: str | None = None  # z.B. "F90", "REI 90"
    surface_spread_of_flame: str | None = None
    combustible: bool | None = None

    # Akustik
    acoustic_rating: str | None = None  # Schallschutzklasse
    sound_transmission_class: int | None = None  # STC

    # Thermik (für Außenbauteile)
    thermal_transmittance: Decimal | None = None  # U-Wert W/(m²·K)

    # Türen/Fenster spezifisch
    operation_type: str | None = None  # SINGLE_SWING_LEFT, SLIDING, etc.
    panel_operation: str | None = None  # Flügelart
    glass_layers: int | None = None  # Anzahl Glasschichten

    # Materialien
    materials: list[ParsedMaterial] = field(default_factory=list)

    # Alle Properties & Quantities
    properties: list[ParsedProperty] = field(default_factory=list)
    quantities: list[ParsedQuantity] = field(default_factory=list)
    classifications: list[ParsedClassification] = field(default_factory=list)

    # Verbundene Elemente
    connected_element_ids: list[str] = field(default_factory=list)
    fills_void_ids: list[str] = field(default_factory=list)
    has_openings_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "global_id": self.global_id,
            "ifc_class": self.ifc_class,
            "name": self.name,
            "description": self.description,
            "object_type": self.object_type,
            "tag": self.tag,
            # Referenzen
            "references": {
                "storey_global_id": self.storey_global_id,
                "type_global_id": self.type_global_id,
                "host_element_id": self.host_element_id,
            },
            # Position
            "position": {
                "x": float(self.position_x) if self.position_x else None,
                "y": float(self.position_y) if self.position_y else None,
                "z": float(self.position_z) if self.position_z else None,
            },
            # Geometrie
            "geometry": {
                "length_m": float(self.length_m) if self.length_m else None,
                "width_m": float(self.width_m) if self.width_m else None,
                "height_m": float(self.height_m) if self.height_m else None,
                "thickness_m": float(self.thickness_m) if self.thickness_m else None,
                "area_m2": float(self.area_m2) if self.area_m2 else None,
                "gross_area_m2": float(self.gross_area_m2) if self.gross_area_m2 else None,
                "net_area_m2": float(self.net_area_m2) if self.net_area_m2 else None,
                "opening_area_m2": float(self.opening_area_m2) if self.opening_area_m2 else None,
                "volume_m3": float(self.volume_m3) if self.volume_m3 else None,
            },
            # Flags
            "flags": {
                "is_external": self.is_external,
                "is_load_bearing": self.is_load_bearing,
            },
            # Brandschutz
            "fire_protection": {
                "fire_rating": self.fire_rating,
                "surface_spread_of_flame": self.surface_spread_of_flame,
                "combustible": self.combustible,
            },
            # Akustik
            "acoustics": {
                "acoustic_rating": self.acoustic_rating,
                "sound_transmission_class": self.sound_transmission_class,
            },
            # Thermik
            "thermal": {
                "thermal_transmittance_u_value": (
                    float(self.thermal_transmittance) if self.thermal_transmittance else None
                ),
            },
            # Türen/Fenster
            "door_window": {
                "operation_type": self.operation_type,
                "panel_operation": self.panel_operation,
                "glass_layers": self.glass_layers,
            },
            # Materialien
            "materials": [m.to_dict() for m in self.materials],
            # Alle Properties
            "properties": [p.to_dict() for p in self.properties],
            "quantities": [q.to_dict() for q in self.quantities],
            "classifications": [c.to_dict() for c in self.classifications],
            # Beziehungen
            "relationships": {
                "connected_element_ids": self.connected_element_ids,
                "fills_void_ids": self.fills_void_ids,
                "has_openings_ids": self.has_openings_ids,
            },
        }


@dataclass
class ParsedElementType:
    """IFC Element Type (Typendefinition)."""

    global_id: str
    ifc_class: str  # z.B. "IfcWallType", "IfcDoorType"
    name: str | None = None
    description: str | None = None
    element_type: str | None = None  # PredefinedType

    # Alle Properties am Typ
    properties: list[ParsedProperty] = field(default_factory=list)
    quantities: list[ParsedQuantity] = field(default_factory=list)
    classifications: list[ParsedClassification] = field(default_factory=list)

    # Materialien (oft am Typ definiert)
    materials: list[ParsedMaterial] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "global_id": self.global_id,
            "ifc_class": self.ifc_class,
            "name": self.name,
            "description": self.description,
            "element_type": self.element_type,
            "properties": [p.to_dict() for p in self.properties],
            "quantities": [q.to_dict() for q in self.quantities],
            "classifications": [c.to_dict() for c in self.classifications],
            "materials": [m.to_dict() for m in self.materials],
        }


# =============================================================================
# DATACLASS - Complete Project
# =============================================================================


@dataclass
class ParsedProject:
    """Komplettes IFC Projekt mit allen extrahierten Daten."""

    name: str
    description: str | None = None
    schema_version: IfcSchemaVersion = IfcSchemaVersion.IFC4

    # File Info
    file_path: str | None = None
    file_hash: str | None = None
    file_size_bytes: int | None = None

    # Authoring
    authoring_app: str | None = None
    authoring_app_version: str | None = None
    author: str | None = None
    organization: str | None = None
    creation_date: str | None = None

    # Räumliche Struktur
    sites: list[ParsedSite] = field(default_factory=list)
    buildings: list[ParsedBuilding] = field(default_factory=list)
    storeys: list[ParsedStorey] = field(default_factory=list)
    spaces: list[ParsedSpace] = field(default_factory=list)

    # Element Types
    element_types: list[ParsedElementType] = field(default_factory=list)

    # Elemente
    elements: list[ParsedElement] = field(default_factory=list)

    # Alle verwendeten Materialien
    all_materials: set[str] = field(default_factory=set)

    # Statistiken
    element_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project": {
                "name": self.name,
                "description": self.description,
                "schema_version": self.schema_version.value,
            },
            "file_info": {
                "path": self.file_path,
                "hash": self.file_hash,
                "size_bytes": self.file_size_bytes,
            },
            "authoring": {
                "application": self.authoring_app,
                "version": self.authoring_app_version,
                "author": self.author,
                "organization": self.organization,
                "creation_date": self.creation_date,
            },
            "spatial_structure": {
                "sites": [s.to_dict() for s in self.sites],
                "buildings": [b.to_dict() for b in self.buildings],
                "storeys": [s.to_dict() for s in self.storeys],
                "spaces": [s.to_dict() for s in self.spaces],
            },
            "element_types": [t.to_dict() for t in self.element_types],
            "elements": [e.to_dict() for e in self.elements],
            "all_materials": list(self.all_materials),
            "statistics": {
                "element_counts": self.element_counts,
                "total_elements": len(self.elements),
                "total_spaces": len(self.spaces),
                "total_storeys": len(self.storeys),
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Export als JSON String."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_json(self, output_path: Union[str, Path]) -> None:
        """Speichert als JSON Datei."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
