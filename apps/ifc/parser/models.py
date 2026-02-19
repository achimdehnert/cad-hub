"""
IFC Complete Parser - Extrahiert ALLE Informationen aus IFC-Dateien

Unterstützt:
- IFC2X3, IFC4, IFC4X1, IFC4X2, IFC4X3
- Alle PropertySets (Pset_*)
- Alle BaseQuantities (Qto_*)
- Materialien (Schichten, Materialsets)
- Klassifikationen (Omniclass, Uniclass, etc.)
- Räumliche Struktur (Site, Building, Storeys, Spaces)
- Alle Bauelemente mit vollständigen Eigenschaften
- Brandschutz, Akustik, Thermik Properties
- Beziehungen und Abhängigkeiten

Autor: BauCAD Hub
Version: 2.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

# =============================================================================
# ENUMS
# =============================================================================


class IfcSchemaVersion(StrEnum):
    """Unterstützte IFC Schema Versionen."""

    IFC2X3 = "IFC2X3"
    IFC4 = "IFC4"
    IFC4X1 = "IFC4X1"
    IFC4X2 = "IFC4X2"
    IFC4X3 = "IFC4X3"


class PropertyDataType(StrEnum):
    """IFC Property Datentypen."""

    STRING = "string"
    INTEGER = "integer"
    REAL = "real"
    BOOLEAN = "boolean"
    LABEL = "label"
    IDENTIFIER = "identifier"
    TEXT = "text"
    MEASURE = "measure"
    ENUM = "enum"
    REFERENCE = "reference"
    LIST = "list"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


# =============================================================================
# DATACLASSES - Properties & Quantities
# =============================================================================


@dataclass
class ParsedProperty:
    """Einzelne IFC Property."""

    pset_name: str  # Name des PropertySets (z.B. "Pset_WallCommon")
    name: str  # Property Name (z.B. "FireRating")
    value: Any  # Wert
    data_type: PropertyDataType = PropertyDataType.STRING
    unit: str | None = None  # Einheit falls vorhanden
    description: str | None = None  # Beschreibung falls vorhanden

    def to_dict(self) -> dict:
        return {
            "pset_name": self.pset_name,
            "name": self.name,
            "value": self.value,
            "data_type": self.data_type.value,
            "unit": self.unit,
            "description": self.description,
        }


@dataclass
class ParsedQuantity:
    """IFC Quantity (Mengenermittlung)."""

    qto_name: str  # Name des QuantitySets (z.B. "Qto_WallBaseQuantities")
    name: str  # Quantity Name (z.B. "NetSideArea")
    value: Decimal | None = None  # Numerischer Wert
    unit: str | None = None  # Einheit (m², m³, m, etc.)
    formula: str | None = None  # Berechnungsformel falls vorhanden
    quantity_type: str = "area"  # length, area, volume, count, weight, time

    def to_dict(self) -> dict:
        return {
            "qto_name": self.qto_name,
            "name": self.name,
            "value": float(self.value) if self.value else None,
            "unit": self.unit,
            "formula": self.formula,
            "quantity_type": self.quantity_type,
        }


@dataclass
class ParsedMaterial:
    """IFC Material (einzelne Schicht oder Material)."""

    name: str  # Material Name
    thickness: Decimal | None = None  # Schichtdicke in Metern
    layer_order: int = 0  # Reihenfolge bei mehrschichtigen Aufbauten
    is_ventilated: bool = False  # Hinterlüftete Schicht
    category: str | None = None  # Kategorie (z.B. "Dämmung", "Tragschicht")

    # Material-Properties
    density: Decimal | None = None  # kg/m³
    thermal_conductivity: Decimal | None = None  # W/(m·K)
    specific_heat: Decimal | None = None  # J/(kg·K)
    fire_rating: str | None = None  # Brandschutzklasse

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "thickness_m": float(self.thickness) if self.thickness else None,
            "layer_order": self.layer_order,
            "is_ventilated": self.is_ventilated,
            "category": self.category,
            "density_kg_m3": float(self.density) if self.density else None,
            "thermal_conductivity_w_mk": (
                float(self.thermal_conductivity) if self.thermal_conductivity else None
            ),
            "fire_rating": self.fire_rating,
        }


@dataclass
class ParsedClassification:
    """IFC Classification Reference (Omniclass, Uniclass, etc.)."""

    system: str  # Klassifikationssystem (z.B. "Omniclass")
    code: str  # Code (z.B. "23-13 00 00")
    name: str | None = None  # Bezeichnung
    location: str | None = None  # URL zur Spezifikation

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "code": self.code,
            "name": self.name,
            "location": self.location,
        }


# =============================================================================
# DATACLASSES - Spatial Structure
# =============================================================================


@dataclass
class ParsedSite:
    """IFC Site (Grundstück)."""

    global_id: str
    name: str | None = None
    description: str | None = None

    # Geolocation
    latitude: float | None = None
    longitude: float | None = None
    elevation: float | None = None

    # Address
    address_lines: list[str] = field(default_factory=list)
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None

    properties: list[ParsedProperty] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "global_id": self.global_id,
            "name": self.name,
            "description": self.description,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation": self.elevation,
            "address": {
                "lines": self.address_lines,
                "postal_code": self.postal_code,
                "city": self.city,
                "country": self.country,
            },
            "properties": [p.to_dict() for p in self.properties],
        }


@dataclass
class ParsedBuilding:
    """IFC Building (Gebäude)."""

    global_id: str
    name: str | None = None
    long_name: str | None = None
    description: str | None = None

    # Building Info
    building_type: str | None = None  # Nutzungsart
    construction_year: int | None = None

    # Elevation
    elevation_of_ref_height: float | None = None
    elevation_of_terrain: float | None = None

    properties: list[ParsedProperty] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "global_id": self.global_id,
            "name": self.name,
            "long_name": self.long_name,
            "description": self.description,
            "building_type": self.building_type,
            "construction_year": self.construction_year,
            "elevation_of_ref_height": self.elevation_of_ref_height,
            "elevation_of_terrain": self.elevation_of_terrain,
            "properties": [p.to_dict() for p in self.properties],
        }


@dataclass
class ParsedStorey:
    """IFC Building Storey (Geschoss)."""

    global_id: str
    name: str | None = None
    long_name: str | None = None
    description: str | None = None

    elevation: float | None = None  # Geschosshöhe über NN
    height: float | None = None  # Geschosshöhe (Rohbau)

    # Referenzen
    building_global_id: str | None = None

    properties: list[ParsedProperty] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "global_id": self.global_id,
            "name": self.name,
            "long_name": self.long_name,
            "description": self.description,
            "elevation": self.elevation,
            "height": self.height,
            "building_global_id": self.building_global_id,
            "properties": [p.to_dict() for p in self.properties],
        }


# =============================================================================
# DATACLASSES - Spaces (Räume)
# =============================================================================


@dataclass
class ParsedSpace:
    """IFC Space (Raum) mit allen Properties."""

    global_id: str
    name: str | None = None
    long_name: str | None = None  # Langname
    space_number: str | None = None  # Raumnummer
    description: str | None = None

    # Referenzen
    storey_global_id: str | None = None
    space_type_global_id: str | None = None

    # Geometrie - BaseQuantities
    net_floor_area: Decimal | None = None  # Netto-Grundfläche
    gross_floor_area: Decimal | None = None  # Brutto-Grundfläche
    net_wall_area: Decimal | None = None  # Wandfläche netto
    net_ceiling_area: Decimal | None = None  # Deckenfläche netto
    net_volume: Decimal | None = None  # Raumvolumen netto
    gross_volume: Decimal | None = None  # Raumvolumen brutto
    net_perimeter: Decimal | None = None  # Umfang
    net_height: Decimal | None = None  # Raumhöhe (lichte Höhe)
    gross_height: Decimal | None = None  # Brutto-Höhe

    # Nutzung
    occupancy_type: str | None = None  # Nutzungsart (DIN 277)
    occupancy_number: int | None = None  # Max. Personenzahl

    # Brandschutz
    fire_compartment: str | None = None  # Brandabschnitt
    fire_rating: str | None = None  # Feuerwiderstandsklasse
    sprinkler_protected: bool = False  # Sprinkler vorhanden

    # ATEX / Explosionsschutz
    ex_zone: str | None = None  # Ex-Zone (0, 1, 2, 20, 21, 22)

    # Akustik
    acoustic_rating: str | None = None  # Schallschutzklasse
    reverberation_time: Decimal | None = None  # Nachhallzeit

    # Thermik
    design_heating_load: Decimal | None = None  # W
    design_cooling_load: Decimal | None = None  # W
    design_temperature_heating: Decimal | None = None  # °C
    design_temperature_cooling: Decimal | None = None  # °C
    humidity_min: Decimal | None = None  # % rel. Luftfeuchte
    humidity_max: Decimal | None = None  # % rel. Luftfeuchte

    # Oberflächen (Finishes)
    finish_floor: str | None = None  # Bodenbelag
    finish_wall: str | None = None  # Wandoberfläche
    finish_ceiling: str | None = None  # Deckenoberfläche
    finish_floor_rating: str | None = None  # Bodenbelag-Klasse (Rutschfestigkeit etc.)

    # Beleuchtung
    illuminance: Decimal | None = None  # Lux (Beleuchtungsstärke)

    # Elektro
    electrical_load: Decimal | None = None  # kW

    # Begrenzende Elemente
    boundary_element_ids: list[str] = field(default_factory=list)

    # Türen und Fenster im Raum
    door_ids: list[str] = field(default_factory=list)
    window_ids: list[str] = field(default_factory=list)

    # Alle Properties (für nicht-standard Properties)
    properties: list[ParsedProperty] = field(default_factory=list)
    quantities: list[ParsedQuantity] = field(default_factory=list)
    classifications: list[ParsedClassification] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "global_id": self.global_id,
            "name": self.name,
            "long_name": self.long_name,
            "space_number": self.space_number,
            "description": self.description,
            "storey_global_id": self.storey_global_id,
            # Geometrie
            "geometry": {
                "net_floor_area_m2": float(self.net_floor_area) if self.net_floor_area else None,
                "gross_floor_area_m2": (
                    float(self.gross_floor_area) if self.gross_floor_area else None
                ),
                "net_wall_area_m2": float(self.net_wall_area) if self.net_wall_area else None,
                "net_ceiling_area_m2": (
                    float(self.net_ceiling_area) if self.net_ceiling_area else None
                ),
                "net_volume_m3": float(self.net_volume) if self.net_volume else None,
                "gross_volume_m3": float(self.gross_volume) if self.gross_volume else None,
                "net_perimeter_m": float(self.net_perimeter) if self.net_perimeter else None,
                "net_height_m": float(self.net_height) if self.net_height else None,
            },
            # Nutzung
            "usage": {
                "occupancy_type": self.occupancy_type,
                "occupancy_number": self.occupancy_number,
            },
            # Brandschutz
            "fire_protection": {
                "fire_compartment": self.fire_compartment,
                "fire_rating": self.fire_rating,
                "sprinkler_protected": self.sprinkler_protected,
                "ex_zone": self.ex_zone,
            },
            # Akustik
            "acoustics": {
                "acoustic_rating": self.acoustic_rating,
                "reverberation_time_s": (
                    float(self.reverberation_time) if self.reverberation_time else None
                ),
            },
            # Thermik
            "thermal": {
                "design_heating_load_w": (
                    float(self.design_heating_load) if self.design_heating_load else None
                ),
                "design_cooling_load_w": (
                    float(self.design_cooling_load) if self.design_cooling_load else None
                ),
                "design_temperature_heating_c": (
                    float(self.design_temperature_heating)
                    if self.design_temperature_heating
                    else None
                ),
                "design_temperature_cooling_c": (
                    float(self.design_temperature_cooling)
                    if self.design_temperature_cooling
                    else None
                ),
                "humidity_min_percent": float(self.humidity_min) if self.humidity_min else None,
                "humidity_max_percent": float(self.humidity_max) if self.humidity_max else None,
            },
            # Oberflächen
            "finishes": {
                "floor": self.finish_floor,
                "wall": self.finish_wall,
                "ceiling": self.finish_ceiling,
                "floor_rating": self.finish_floor_rating,
            },
            # Beleuchtung & Elektro
            "electrical": {
                "illuminance_lux": float(self.illuminance) if self.illuminance else None,
                "electrical_load_kw": float(self.electrical_load) if self.electrical_load else None,
            },
            # Beziehungen
            "related_elements": {
                "boundary_element_ids": self.boundary_element_ids,
                "door_ids": self.door_ids,
                "window_ids": self.window_ids,
            },
            # Alle Properties
            "properties": [p.to_dict() for p in self.properties],
            "quantities": [q.to_dict() for q in self.quantities],
            "classifications": [c.to_dict() for c in self.classifications],
        }


# Re-export element models for backward compatibility
from .models_element import (  # noqa: F401
    ParsedElement,
    ParsedElementType,
    ParsedProject,
)
