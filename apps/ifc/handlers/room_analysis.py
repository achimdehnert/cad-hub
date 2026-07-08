"""
RoomAnalysisHandler — Raum-Extraktion & DIN 277 Klassifikation.

Nutzt nl2cad.core.models.ifc.IFCRoom als Domänenobjekt
und nl2cad.areas.din277.DIN277Calculator für die Klassifikation.
"""

from __future__ import annotations

import logging

from nl2cad.areas.din277 import DIN277Calculator
from nl2cad.core.models.ifc import IFCRoom

from apps.core.handlers.base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)

# Sanity-Grenzen für DXF-Raumflächen — Sicherheitsnetz gegen Fehlerkennungen
# (z. B. Gebäudeumriss/Grundstücksgrenze als "Raum"), unabhängig vom
# Extraktions-Algorithmus. Untergrenze überschneidet sich mit nl2cads eigenem
# DXFParserConfig.min_area_m2 (0.5), bleibt hier zusätzlich als lokaler Guard.
_MIN_ROOM_AREA_M2 = 1.0
_MAX_ROOM_AREA_M2 = 10_000.0


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
                {"name": r.name, "area_m2": r.area_m2, "din277_code": r.din277_code} for r in rooms
            ]
            din277_result = self._din277.calculate(rooms_data)
            din277_summary = self._build_summary(din277_result)

        result.data.update(
            {
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
            }
        )

        result.status = HandlerStatus.SUCCESS
        logger.info(
            "[%s] %d Räume, %.1f m²",
            self.name,
            len(rooms),
            total_area_m2,
        )
        return result

    def _extract_dxf_rooms(self, loader, result: CADHandlerResult) -> list[IFCRoom]:
        """
        Extrahiert Räume aus DXF-Loader als IFCRoom-Liste.

        get_rooms()/get_room_areas() lesen beide aus derselben
        nl2cad-DXFModel.rooms-Liste (loader.dxf_model) in derselben
        Reihenfolge (ADR-012 T2) — Name und Fläche sind damit per Index
        bereits demselben erkannten Raum zugeordnet, kein Layer-Name-Matching
        mehr nötig. Layer-Ausschluss (Wand/Symbol/Bemaßung/...) passiert
        bereits in nl2cads DXFParserConfig beim Parsen (siehe cad_loader.py).
        """
        rooms: list[IFCRoom] = []
        skipped = 0

        try:
            names = loader.get_rooms()
            areas = loader.get_room_areas()
            for name_info, area_info in zip(names, areas, strict=True):
                area_m2 = area_info.get("area", 0)
                if area_m2 < _MIN_ROOM_AREA_M2 or area_m2 > _MAX_ROOM_AREA_M2:
                    skipped += 1
                    continue
                rooms.append(
                    IFCRoom(
                        name=name_info.get("name") or "Unbekannt",
                        area_m2=area_m2,
                        perimeter_m=area_info.get("perimeter", 0),
                        floor_name=name_info.get("layer", ""),
                    )
                )
            if skipped:
                result.add_warning(f"{skipped} Räume außerhalb Flächen-Sanity-Grenzen übersprungen")
            logger.info("[%s] %d Räume aus DXF extrahiert", self.name, len(rooms))
        except Exception as e:
            result.add_warning(f"DXF-Raumerkennung fehlgeschlagen: {e}")

        # Fallback: Bounding Box
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
                        rooms.append(
                            IFCRoom(
                                name="Geschätzte Gesamtfläche",
                                area_m2=estimated,
                                floor_name="ESTIMATE",
                            )
                        )
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
