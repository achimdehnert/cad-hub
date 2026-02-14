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

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.shape
import ifcopenshell.util.unit

# =============================================================================
# ENUMS
# =============================================================================


class IfcSchemaVersion(str, Enum):
    """Unterstützte IFC Schema Versionen."""

    IFC2X3 = "IFC2X3"
    IFC4 = "IFC4"
    IFC4X1 = "IFC4X1"
    IFC4X2 = "IFC4X2"
    IFC4X3 = "IFC4X3"


class PropertyDataType(str, Enum):
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
    unit: Optional[str] = None  # Einheit falls vorhanden
    description: Optional[str] = None  # Beschreibung falls vorhanden

    def to_dict(self) -> Dict:
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
    value: Optional[Decimal] = None  # Numerischer Wert
    unit: Optional[str] = None  # Einheit (m², m³, m, etc.)
    formula: Optional[str] = None  # Berechnungsformel falls vorhanden
    quantity_type: str = "area"  # length, area, volume, count, weight, time

    def to_dict(self) -> Dict:
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
    thickness: Optional[Decimal] = None  # Schichtdicke in Metern
    layer_order: int = 0  # Reihenfolge bei mehrschichtigen Aufbauten
    is_ventilated: bool = False  # Hinterlüftete Schicht
    category: Optional[str] = None  # Kategorie (z.B. "Dämmung", "Tragschicht")

    # Material-Properties
    density: Optional[Decimal] = None  # kg/m³
    thermal_conductivity: Optional[Decimal] = None  # W/(m·K)
    specific_heat: Optional[Decimal] = None  # J/(kg·K)
    fire_rating: Optional[str] = None  # Brandschutzklasse

    def to_dict(self) -> Dict:
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
    name: Optional[str] = None  # Bezeichnung
    location: Optional[str] = None  # URL zur Spezifikation

    def to_dict(self) -> Dict:
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
    name: Optional[str] = None
    description: Optional[str] = None

    # Geolocation
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None

    # Address
    address_lines: List[str] = field(default_factory=list)
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    properties: List[ParsedProperty] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
    name: Optional[str] = None
    long_name: Optional[str] = None
    description: Optional[str] = None

    # Building Info
    building_type: Optional[str] = None  # Nutzungsart
    construction_year: Optional[int] = None

    # Elevation
    elevation_of_ref_height: Optional[float] = None
    elevation_of_terrain: Optional[float] = None

    properties: List[ParsedProperty] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
    name: Optional[str] = None
    long_name: Optional[str] = None
    description: Optional[str] = None

    elevation: Optional[float] = None  # Geschosshöhe über NN
    height: Optional[float] = None  # Geschosshöhe (Rohbau)

    # Referenzen
    building_global_id: Optional[str] = None

    properties: List[ParsedProperty] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
    name: Optional[str] = None
    long_name: Optional[str] = None  # Langname
    space_number: Optional[str] = None  # Raumnummer
    description: Optional[str] = None

    # Referenzen
    storey_global_id: Optional[str] = None
    space_type_global_id: Optional[str] = None

    # Geometrie - BaseQuantities
    net_floor_area: Optional[Decimal] = None  # Netto-Grundfläche
    gross_floor_area: Optional[Decimal] = None  # Brutto-Grundfläche
    net_wall_area: Optional[Decimal] = None  # Wandfläche netto
    net_ceiling_area: Optional[Decimal] = None  # Deckenfläche netto
    net_volume: Optional[Decimal] = None  # Raumvolumen netto
    gross_volume: Optional[Decimal] = None  # Raumvolumen brutto
    net_perimeter: Optional[Decimal] = None  # Umfang
    net_height: Optional[Decimal] = None  # Raumhöhe (lichte Höhe)
    gross_height: Optional[Decimal] = None  # Brutto-Höhe

    # Nutzung
    occupancy_type: Optional[str] = None  # Nutzungsart (DIN 277)
    occupancy_number: Optional[int] = None  # Max. Personenzahl

    # Brandschutz
    fire_compartment: Optional[str] = None  # Brandabschnitt
    fire_rating: Optional[str] = None  # Feuerwiderstandsklasse
    sprinkler_protected: bool = False  # Sprinkler vorhanden

    # ATEX / Explosionsschutz
    ex_zone: Optional[str] = None  # Ex-Zone (0, 1, 2, 20, 21, 22)

    # Akustik
    acoustic_rating: Optional[str] = None  # Schallschutzklasse
    reverberation_time: Optional[Decimal] = None  # Nachhallzeit

    # Thermik
    design_heating_load: Optional[Decimal] = None  # W
    design_cooling_load: Optional[Decimal] = None  # W
    design_temperature_heating: Optional[Decimal] = None  # °C
    design_temperature_cooling: Optional[Decimal] = None  # °C
    humidity_min: Optional[Decimal] = None  # % rel. Luftfeuchte
    humidity_max: Optional[Decimal] = None  # % rel. Luftfeuchte

    # Oberflächen (Finishes)
    finish_floor: Optional[str] = None  # Bodenbelag
    finish_wall: Optional[str] = None  # Wandoberfläche
    finish_ceiling: Optional[str] = None  # Deckenoberfläche
    finish_floor_rating: Optional[str] = None  # Bodenbelag-Klasse (Rutschfestigkeit etc.)

    # Beleuchtung
    illuminance: Optional[Decimal] = None  # Lux (Beleuchtungsstärke)

    # Elektro
    electrical_load: Optional[Decimal] = None  # kW

    # Begrenzende Elemente
    boundary_element_ids: List[str] = field(default_factory=list)

    # Türen und Fenster im Raum
    door_ids: List[str] = field(default_factory=list)
    window_ids: List[str] = field(default_factory=list)

    # Alle Properties (für nicht-standard Properties)
    properties: List[ParsedProperty] = field(default_factory=list)
    quantities: List[ParsedQuantity] = field(default_factory=list)
    classifications: List[ParsedClassification] = field(default_factory=list)

    def to_dict(self) -> Dict:
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
