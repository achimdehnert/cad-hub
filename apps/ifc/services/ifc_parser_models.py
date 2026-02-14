"""
IFC Parser Data Models

Enums and dataclasses for IFC parsing results.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RoomType(Enum):
    """DIN 277 Raumtypen"""

    NF1_WOHNEN = "NF1.1"
    NF1_BUERO = "NF1.2"
    NF2 = "NF2"
    NF3 = "NF3"
    NF4 = "NF4"
    NF5 = "NF5"
    NF6 = "NF6"
    TF7 = "TF7"
    VF8 = "VF8"
    UNKNOWN = ""


# Mapping RoomType → Django Model UsageCategory
ROOMTYPE_TO_USAGE = {
    RoomType.NF1_WOHNEN: "NF1.1",
    RoomType.NF1_BUERO: "NF1.2",
    RoomType.NF2: "NF2",
    RoomType.NF3: "NF3",
    RoomType.NF4: "NF4",
    RoomType.NF5: "NF5",
    RoomType.NF6: "NF6",
    RoomType.TF7: "TF7",
    RoomType.VF8: "VF8",
}


@dataclass
class ParsedFloor:
    """Geparstes Geschoss"""

    ifc_guid: str
    name: str
    elevation: float
    rooms_count: int = 0


@dataclass
class ParsedRoom:
    """Geparseter Raum mit DIN 277 Klassifizierung"""

    ifc_guid: str
    number: str
    name: str
    long_name: str = ""
    area: float = 0.0
    height: float = 0.0
    volume: float = 0.0
    perimeter: float = 0.0
    floor_guid: Optional[str] = None
    room_type: RoomType = RoomType.UNKNOWN
    properties: dict = field(default_factory=dict)

    @property
    def usage_category(self) -> str:
        """Gibt Django Model UsageCategory zurück"""
        return ROOMTYPE_TO_USAGE.get(self.room_type, "")


@dataclass
class ParsedWindow:
    """Geparstes Fenster"""

    ifc_guid: str
    number: str = ""
    name: str = ""
    width: float = 0.0
    height: float = 0.0
    area: float = 0.0
    floor_guid: Optional[str] = None
    material: str = ""
    u_value: Optional[float] = None
    properties: dict = field(default_factory=dict)


@dataclass
class ParsedDoor:
    """Gepars te Tür"""

    ifc_guid: str
    number: str = ""
    name: str = ""
    width: float = 0.0
    height: float = 0.0
    door_type: str = ""
    floor_guid: Optional[str] = None
    material: str = ""
    fire_rating: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class ParsedWall:
    """Gepars te Wand"""

    ifc_guid: str
    name: str = ""
    length: float = 0.0
    height: float = 0.0
    width: float = 0.0
    gross_area: float = 0.0
    net_area: float = 0.0
    volume: float = 0.0
    floor_guid: Optional[str] = None
    is_external: bool = False
    is_load_bearing: bool = False
    material: str = ""


@dataclass
class ParsedSlab:
    """Gepars te Decke/Platte"""

    ifc_guid: str
    name: str = ""
    slab_type: str = "FLOOR"
    area: float = 0.0
    thickness: float = 0.0
    volume: float = 0.0
    perimeter: float = 0.0
    floor_guid: Optional[str] = None
    material: str = ""


@dataclass
class IFCParseResult:
    """Ergebnis des IFC Parsings"""

    schema: str = ""
    application: str = ""
    project_name: str = ""
    floors: List[ParsedFloor] = field(default_factory=list)
    rooms: List[ParsedRoom] = field(default_factory=list)
    windows: List[ParsedWindow] = field(default_factory=list)
    doors: List[ParsedDoor] = field(default_factory=list)
    walls: List[ParsedWall] = field(default_factory=list)
    slabs: List[ParsedSlab] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_area(self) -> float:
        return sum(r.area for r in self.rooms)


