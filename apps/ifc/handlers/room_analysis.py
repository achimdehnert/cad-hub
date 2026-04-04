"""
RoomAnalysisHandler — Raum-Extraktion & DIN 277 Klassifikation.

Nutzt nl2cad.core.models.ifc.IFCRoom als Domänenobjekt
und nl2cad.areas.din277.DIN277Calculator für die Klassifikation.
"""
from __future__ import annotations

import logging

from nl2cad_areas.din277 import DIN277Calculator
from nl2cad_core.models.ifc import IFCRoom

from apps.core.handlers.base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


# Layer-Keywords für DXF-Raumerkennung
_EXCLUDED_LAYER_KEYWORDS = [
    "symbol", "schraffur", "hatch", "text", "beschriftung", "annotation",
    "bemaßung", "dimension", "dim", "achse", "axis", "grid", "hilfslin",
    "construction", "möbel", "furniture", "einrichtung", "elektro", "sanitär",
    "heizung", "lüftung", "hvac", "legende", "rahmen", "frame", "border",
    "logo", "titel", "viewport", "defpoints", "decken", "ceiling",
    "deckenkonstruktion", "fußbodenaufbau", "wand", "wände", "wall",
    "konstruktion", "tragwerk", "fundament", "dach", "roof", "fassade",
    "treppe", "stair", "aufzug", "elevator",
]

_VALID_FLOOR_KEYWORDS = [
    "raum", "räume", "room", "nutzfläche", "nutzflaeche", "nuf",
    "bodenplatte", "grundriss", "wohnfläche", "büro", "buero", "office",
    "flur", "corridor", "küche", "kueche", "kitchen", "bad", "wc",
    "schlaf", "wohn", "lager", "storage", "keller", "basement", "garage",
]


def _is_excluded_layer(layer_name: str) -> bool:
    layer_lower = layer_name.lower()
    if layer_name.startswith("\\") or "{\\p" in layer_name or "\\f" in layer_name:
        return True
    return any(kw in layer_lower for kw in _EXCLUDED_LAYER_KEYWORDS)


def _is_valid_floor_layer(layer_name: str) -> bool:
    layer_lower = layer_name.lower()
    return any(kw in layer_lower for kw in _VALID_FLOOR_KEYWORDS)


def _get_unit_factor(loader, room_areas: list) -> float:
    """Ermittelt Umrechnungsfaktor für Flächen zu m²."""
    try:
        analysis = loader.get_analysis()
        units = getattr(analysis, "units", None)
        if units:
            units_lower = str(units).lower()
            if "mm" in units_lower:
                return 1 / 1_000_000
            if "cm" in units_lower:
                return 1 / 10_000
            if "m" in units_lower:
                return 1.0
    except Exception:
        pass
    if not room_areas:
        return 1.0
    max_area = max(a.get("area", 0) for a in room_areas)
    if max_area > 1_000_000:
        return 1 / 1_000_000
    if max_area > 10_000:
        return 1 / 10_000
    return 1.0


class RoomAnalysisHandler(BaseCADHandler):
    """
    Handler für Raum-Analyse und DIN 277 Klassifikation.

    Nutzt nl2cad.core.models.ifc.IFCRoom + nl2cad.areas.din277.DIN277Calculator.

    Input:
        loader: CADLoaderService (von CADFileInputHandler) — DXF-Pfad
        ifc_result: IFCModel — IFC-Pfad
        classify_din277: bool (default True)

    Output:
        rooms: Liste der erkannten Räume (dicts)
        total_area_m2: Gesamtfläche in m²
        din277_result: DIN277Result.to_dict()
        din277_summary: Rückwärtscompat. summary dict
        doors: Erkannte Türen
        windows: Erkannte Fenster
    """

    name = "RoomAnalysisHandler"
    description = "Raum-Extraktion & DIN 277 Klassifikation (via nl2cad)"
    required_inputs = []
    optional_inputs = ["loader", "ifc_result", "classify_din277"]

    def __init__(self) -> None:
        super().__init__()
        self._din277 = DIN277Calculator()

    def execute(self, input_data: dict) -> CADHandlerResult:
        """Analysiert Räume und berechnet DIN 277."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )

        loader = input_data.get("_loader") or input_data.get("loader")
        ifc_result = input_data.get("ifc_result")
        classify_din277 = input_data.get("classify_din277", True)

        if not loader and not ifc_result:
            result.add_error("Keine CAD-Daten (loader oder ifc_result)")
            return result

        rooms: list[IFCRoom] = []
        doors: list[dict] = []
        windows: list[dict] = []

        if ifc_result:
            rooms = list(ifc_result.rooms)
        elif loader:
            rooms = self._extract_dxf_rooms(loader, result)
            doors = self._get_doors(loader)
            windows = self._get_windows(loader)

        rooms = self._deduplicate(rooms, result)

        total_area_m2 = sum(r.area_m2 for r in rooms)

        din277_result = None
        din277_summary: dict = {}
        if classify_din277 and rooms:
            rooms_data = [
                {"name": r.name, "area_m2": r.area_m2, "din277_code": r.din277_code}
                for r in rooms
            ]
            din277_result = self._din277.calculate(rooms_data)
            din277_summary = self._build_summary(din277_result)

        result.data.update({
            "rooms": [self._room_to_dict(r) for r in rooms],
            "room_count": len(rooms),
            "total_area_m2": total_area_m2,
            "total_area": total_area_m2,
            "total_area_formatted": f"{total_area_m2:.2f} m²",
            "din277_result": din277_result.to_dict() if din277_result else {},
            "din277_summary": din277_summary,
            "doors": doors,
            "door_count": len(doors),
            "windows": windows,
            "window_count": len(windows),
        })

        result.status = HandlerStatus.SUCCESS
        logger.info(
            "[%s] %d Räume, %.1f m²",
            self.name, len(rooms), total_area_m2,
        )
        return result

    def _extract_dxf_rooms(self, loader, result: CADHandlerResult) -> list[IFCRoom]:
        """Extrahiert Räume aus DXF-Loader als IFCRoom-Liste."""
        rooms: list[IFCRoom] = []

        # 1. Text-basierte Raumerkennung
        try:
            for tr in loader.get_rooms():
                rooms.append(IFCRoom(
                    name=tr.get("name", "Unbekannt"),
                    floor_name=tr.get("layer", ""),
                ))
        except Exception as e:
            result.add_warning(f"Text-Raumerkennung fehlgeschlagen: {e}")

        # 2. Geometrie-basierte Flächenberechnung
        try:
            room_areas = loader.get_room_areas()
            if room_areas:
                unit_factor = _get_unit_factor(loader, room_areas)
                valid_count = 0
                excluded_count = 0

                for area_info in room_areas:
                    layer = area_info.get("layer", "")

                    if _is_excluded_layer(layer):
                        excluded_count += 1
                        continue
                    if not _is_valid_floor_layer(layer):
                        excluded_count += 1
                        continue

                    area_m2 = area_info.get("area", 0) * unit_factor
                    perimeter_m = area_info.get("perimeter", 0) * (unit_factor ** 0.5)

                    if area_m2 < 1.0 or area_m2 > 10_000:
                        continue

                    matched = False
                    for room in rooms:
                        if room.floor_name == layer and room.area_m2 == 0:
                            room.area_m2 = area_m2
                            room.perimeter_m = perimeter_m
                            matched = True
                            break

                    if not matched:
                        rooms.append(IFCRoom(
                            name=f"Fläche_{layer}" if layer else "Unbenannt",
                            area_m2=area_m2,
                            perimeter_m=perimeter_m,
                            floor_name=layer,
                        ))
                        valid_count += 1

                if excluded_count > 0:
                    result.add_warning(f"{excluded_count} Layer übersprungen")
                logger.info("[%s] %d gültige Nutzflächen", self.name, valid_count)

        except Exception as e:
            result.add_warning(f"Flächen-Berechnung fehlgeschlagen: {e}")

        # 3. Fallback: Bounding Box
        if not any(r.area_m2 > 0 for r in rooms):
            try:
                stats = loader.get_statistics()
                bbox = stats.get("bounding_box", {})
                w, h = bbox.get("width", 0), bbox.get("height", 0)
                if w > 0 and h > 0:
                    estimated = w * h * 0.6
                    if estimated > 1_000_000:
                        estimated /= 1_000_000
                    elif estimated > 10_000:
                        estimated /= 10_000
                    if estimated > 1:
                        result.add_warning(
                            f"Keine Polylinien — Schätzung aus Bounding Box: ~{estimated:.0f} m²"
                        )
                        rooms.append(IFCRoom(
                            name="Geschätzte Gesamtfläche",
                            area_m2=estimated,
                            floor_name="ESTIMATE",
                        ))
            except Exception as e:
                logger.warning("[%s] Bounding-Box-Fallback fehlgeschlagen: %s", self.name, e)

        return rooms

    def _deduplicate(self, rooms: list[IFCRoom], result: CADHandlerResult) -> list[IFCRoom]:
        """Entfernt Duplikate (gleicher Layer + gleiche Fläche)."""
        seen: set[tuple] = set()
        unique: list[IFCRoom] = []
        dupes = 0
        for room in rooms:
            key = (room.floor_name, round(room.area_m2, 1))
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            unique.append(room)
        if dupes:
            result.add_warning(f"{dupes} Duplikate entfernt")
        return unique

    def _get_doors(self, loader) -> list[dict]:
        try:
            return loader.get_doors()
        except Exception:
            return []

    def _get_windows(self, loader) -> list[dict]:
        try:
            return loader.get_windows()
        except Exception:
            return []

    def _build_summary(self, din277_result) -> dict:
        """Baut Rückwärtskompatibles summary-Dict aus DIN277Result."""
        summary: dict = {}
        for code, cat in din277_result.categories.items():
            summary[code] = {
                "category": cat.name,
                "count": cat.room_count,
                "area": cat.area_m2,
                "area_formatted": cat.area_formatted,
            }
        return summary

    def _room_to_dict(self, room: IFCRoom) -> dict:
        """Serialisiert IFCRoom für Template-Nutzung."""
        return {
            "name": room.name,
            "area_m2": room.area_m2,
            "area": room.area_m2,
            "area_formatted": f"{room.area_m2:.2f} m²",
            "perimeter_m": room.perimeter_m,
            "perimeter": room.perimeter_m,
            "layer": room.floor_name,
            "din277_code": room.din277_code,
            "din277_category": room.din277_category,
            "floor": room.floor_number,
            "ifc_id": room.ifc_id,
            "number": room.number,
        }
