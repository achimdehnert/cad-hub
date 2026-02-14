"""
Specialized DXF Analyzers

FloorPlanAnalyzer and TechnicalDrawingAnalyzer — domain-specific
subclasses of DXFAnalyzer.
"""

import re
from collections import Counter

from .dxf_analyzer import DXFAnalyzer


class FloorPlanAnalyzer(DXFAnalyzer):
    """Spezialisierte Analyse für Grundrisse."""

    # Typische Block-Namen für Grundriss-Elemente
    DOOR_PATTERNS = ["DOOR", "TÜR", "TUER", "D-", "DR-"]
    WINDOW_PATTERNS = ["WINDOW", "FENSTER", "W-", "WI-", "FE-"]
    FURNITURE_PATTERNS = [
        "DESK", "TABLE", "CHAIR", "SOFA", "BED",
        "TISCH", "STUHL", "BETT", "SCHRANK",
    ]
    SANITARY_PATTERNS = [
        "WC", "TOILET", "SINK", "BATH", "SHOWER",
        "WASCHBECKEN", "DUSCHE", "BADEWANNE",
    ]

    def find_doors(self) -> list[dict]:
        """Findet Tür-Blöcke."""
        return self._find_blocks_by_pattern(self.DOOR_PATTERNS)

    def find_windows(self) -> list[dict]:
        """Findet Fenster-Blöcke."""
        return self._find_blocks_by_pattern(self.WINDOW_PATTERNS)

    def find_furniture(self) -> list[dict]:
        """Findet Möbel-Blöcke."""
        return self._find_blocks_by_pattern(self.FURNITURE_PATTERNS)

    def find_sanitary(self) -> list[dict]:
        """Findet Sanitär-Blöcke."""
        return self._find_blocks_by_pattern(self.SANITARY_PATTERNS)

    def _find_blocks_by_pattern(self, patterns: list[str]) -> list[dict]:
        """Findet Blöcke die einem Muster entsprechen."""
        results = []

        for insert in self.msp.query("INSERT"):
            name = insert.dxf.name.upper()
            for pattern in patterns:
                if pattern.upper() in name:
                    results.append({
                        "block_name": insert.dxf.name,
                        "position": tuple(insert.dxf.insert),
                        "rotation": insert.dxf.rotation,
                        "layer": insert.dxf.layer,
                        "matched_pattern": pattern,
                    })
                    break

        return results

    def identify_rooms(self) -> list[dict]:
        """
        Versucht Räume anhand von Texten in geschlossenen Bereichen
        zu identifizieren.
        """
        rooms = []
        texts = self.extract_texts()

        # Typische Raumnamen
        room_keywords = [
            "ZIMMER", "RAUM", "KÜCHE", "BAD", "WC", "FLUR", "DIELE",
            "WOHNZIMMER", "SCHLAFZIMMER", "KINDERZIMMER", "ARBEITSZIMMER",
            "KELLER", "GARAGE", "BALKON", "TERRASSE", "LIVING", "BEDROOM",
            "KITCHEN", "BATHROOM", "OFFICE", "ROOM",
        ]

        for text in texts:
            content_upper = text.content.upper()
            for keyword in room_keywords:
                if keyword in content_upper:
                    rooms.append({
                        "name": text.content,
                        "position": text.position,
                        "layer": text.layer,
                    })
                    break

        return rooms

    def calculate_room_areas(self) -> list[dict]:
        """
        Berechnet Flächen geschlossener Polylinien (potenzielle Räume).
        """
        areas = []

        for pline in self.msp.query("LWPOLYLINE"):
            if pline.closed:
                points = list(pline.get_points("xy"))
                area = self._calculate_polygon_area(points)

                if area > 1.0:
                    areas.append({
                        "handle": pline.dxf.handle,
                        "layer": pline.dxf.layer,
                        "area": area,
                        "perimeter": self._calculate_polyline_length(
                            points, True
                        ),
                        "vertex_count": len(points),
                    })

        return sorted(areas, key=lambda x: x["area"], reverse=True)


class TechnicalDrawingAnalyzer(DXFAnalyzer):
    """Spezialisierte Analyse für technische Zeichnungen."""

    def analyze_centerlines(self) -> list[dict]:
        """Findet Mittellinien (typischerweise auf eigenen Layern)."""
        centerline_keywords = [
            "CENTER", "MITTEL", "CL", "AXIS", "ACHSE",
        ]
        results = []

        for layer in self.get_layer_names():
            layer_upper = layer.upper()
            if any(kw in layer_upper for kw in centerline_keywords):
                entities = list(self.get_entities_by_layer(layer))
                results.append({
                    "layer": layer,
                    "entity_count": len(entities),
                    "types": dict(
                        Counter(e.dxftype() for e in entities)
                    ),
                })

        return results

    def extract_holes(self) -> list[dict]:
        """Extrahiert Bohrungen (Kreise mit bestimmten Radien)."""
        holes = []

        for circle in self.msp.query("CIRCLE"):
            radius = circle.dxf.radius
            standard_diameters = [
                3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30,
            ]
            diameter = radius * 2

            is_standard = any(
                abs(diameter - d) < 0.1 for d in standard_diameters
            )

            holes.append({
                "center": tuple(circle.dxf.center),
                "radius": radius,
                "diameter": diameter,
                "is_standard_size": is_standard,
                "layer": circle.dxf.layer,
            })

        return holes

    def extract_tolerances(self) -> list[dict]:
        """Extrahiert Toleranz-Informationen aus Bemaßungen und Texten."""
        tolerances = []

        # Aus Bemaßungen
        for dim in self.extract_dimensions():
            if dim.text_override and (
                "±" in dim.text_override
                or "+/-" in dim.text_override
                or "+" in dim.text_override
            ):
                tolerances.append({
                    "type": "dimension",
                    "value": dim.measurement,
                    "text": dim.text_override,
                    "layer": dim.layer,
                })

        # Aus Texten
        tolerance_pattern = (
            r'[±]\s*[\d.,]+|[\d.,]+\s*[±]\s*[\d.,]+'
        )

        for text in self.extract_texts():
            if re.search(tolerance_pattern, text.content):
                tolerances.append({
                    "type": "text",
                    "content": text.content,
                    "position": text.position,
                    "layer": text.layer,
                })

        return tolerances
