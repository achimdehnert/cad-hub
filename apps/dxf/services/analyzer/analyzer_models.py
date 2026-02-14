"""
DXF Analyzer Data Models

Enums and dataclasses used by DXFAnalyzer and specialized analyzers.
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class EntityCategory(Enum):
    """Kategorisierung von DXF-Entities."""
    PRIMITIVE = auto()      # LINE, POINT
    CURVE = auto()          # ARC, CIRCLE, ELLIPSE, SPLINE
    POLYLINE = auto()       # LWPOLYLINE, POLYLINE
    SURFACE = auto()        # HATCH, SOLID, 3DFACE
    TEXT = auto()           # TEXT, MTEXT
    DIMENSION = auto()      # DIMENSION, LEADER
    REFERENCE = auto()      # INSERT (Block-Referenz)
    OTHER = auto()


ENTITY_CATEGORIES = {
    "POINT": EntityCategory.PRIMITIVE,
    "LINE": EntityCategory.PRIMITIVE,
    "XLINE": EntityCategory.PRIMITIVE,
    "RAY": EntityCategory.PRIMITIVE,
    "CIRCLE": EntityCategory.CURVE,
    "ARC": EntityCategory.CURVE,
    "ELLIPSE": EntityCategory.CURVE,
    "SPLINE": EntityCategory.CURVE,
    "LWPOLYLINE": EntityCategory.POLYLINE,
    "POLYLINE": EntityCategory.POLYLINE,
    "HATCH": EntityCategory.SURFACE,
    "SOLID": EntityCategory.SURFACE,
    "3DFACE": EntityCategory.SURFACE,
    "MESH": EntityCategory.SURFACE,
    "TEXT": EntityCategory.TEXT,
    "MTEXT": EntityCategory.TEXT,
    "ATTRIB": EntityCategory.TEXT,
    "ATTDEF": EntityCategory.TEXT,
    "DIMENSION": EntityCategory.DIMENSION,
    "LEADER": EntityCategory.DIMENSION,
    "TOLERANCE": EntityCategory.DIMENSION,
    "INSERT": EntityCategory.REFERENCE,
}


@dataclass
class LayerInfo:
    """Layer-Informationen."""
    name: str
    color: int
    linetype: str
    is_on: bool
    is_frozen: bool
    is_locked: bool
    entity_count: int = 0
    entity_types: dict = field(default_factory=dict)


@dataclass
class BlockInfo:
    """Block-Informationen."""
    name: str
    base_point: tuple
    entity_count: int
    has_attributes: bool
    attribute_tags: list
    insert_count: int = 0
    insert_positions: list = field(default_factory=list)


@dataclass
class TextInfo:
    """Extrahierte Text-Information."""
    content: str
    position: tuple
    height: float
    rotation: float
    layer: str
    entity_type: str
    style: str = ""


@dataclass
class DimensionInfo:
    """Extrahierte Bemaßungs-Information."""
    measurement: float
    text_override: str
    dim_type: str
    layer: str
    definition_points: list = field(default_factory=list)


@dataclass
class GeometryInfo:
    """Geometrische Entity-Information."""
    entity_type: str
    layer: str
    color: int
    handle: str
    geometry: dict  # Typ-spezifische Geometrie-Daten


@dataclass
class AnalysisReport:
    """Vollständiger Analyse-Report."""
    filename: str
    dxf_version: str
    encoding: str
    units: str

    # Statistiken
    total_entities: int
    entity_statistics: dict
    category_statistics: dict

    # Struktur
    layers: list
    blocks: list

    # Geometrie
    bounding_box: dict
    estimated_area: float

    # Inhalte
    texts: list
    dimensions: list

    # Qualität
    issues: list

    # DWG-spezifisch
    source_format: str = "DXF"
    was_converted: bool = False
