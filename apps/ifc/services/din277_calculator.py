# apps/ifc/services/din277_calculator.py
"""
DIN 277 Thin Wrapper — delegiert an nl2cad.areas.din277.

Behält die bisherige Django-API (calculate_from_rooms, calculate_from_queryset)
für Backward-Kompatibilität. Mapping: Django-Feld 'area' → nl2cad 'area_m2'.
"""

from __future__ import annotations

import logging

from nl2cad.areas.din277 import DIN277Calculator as _NL2CADCalculator
from nl2cad.areas.din277 import DIN277Result

logger = logging.getLogger(__name__)


def _map_room(room: dict) -> dict:
    """Mappt Django-Feldnamen auf nl2cad-Feldnamen."""
    mapped = dict(room)
    if "area" in mapped and "area_m2" not in mapped:
        mapped["area_m2"] = mapped.pop("area")
    return mapped


class DIN277Calculator:
    """
    Django-facing DIN 277 Calculator.
    Delegiert an nl2cad.areas.din277.DIN277Calculator.

    Backward-kompatible API für bestehende cad-hub Views/Services.
    """

    def __init__(self) -> None:
        self._calculator = _NL2CADCalculator()

    def calculate_from_rooms(
        self,
        rooms: list[dict],
        bgf: float | None = None,
        floor_height: float = 3.0,
    ) -> DIN277Result:
        """
        Berechnet DIN 277 aus Raumliste.

        Args:
            rooms: Liste von Dicts mit 'name', 'area' oder 'area_m2', optional 'usage_category'
            bgf: Brutto-Grundfläche (optional, wird an nl2cad-Result als Warning notiert)
            floor_height: Geschosshöhe (ungenutzt — für Backward-Compat)
        """
        mapped = [_map_room(r) for r in rooms]
        result = self._calculator.calculate(mapped)

        if bgf is not None:
            result.warnings.append(
                f"BGF {bgf:.2f} m² übergeben — wird in nl2cad.areas.din277 nicht direkt genutzt"
            )

        logger.info(
            "[DIN277Calculator] %d Räume → NGF %.1f m²",
            len(rooms),
            result.netto_grundflaeche_m2,
        )
        return result

    def calculate_from_queryset(self, rooms_qs, bgf: float | None = None) -> DIN277Result:
        """
        Berechnet DIN 277 direkt aus Django QuerySet.

        Args:
            rooms_qs: Room.objects.filter(...)
            bgf: Optional BGF
        """
        rooms = list(rooms_qs.values("name", "area", "usage_category"))
        return self.calculate_from_rooms(rooms, bgf=bgf)

    def classify_room(self, room_name: str) -> str:
        """Klassifiziert einen Raum nach DIN 277. Gibt DIN277-Code zurück."""
        return self._calculator.classify_room(room_name)
