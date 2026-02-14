"""
DXF/DWG Analyse Toolkit - Haupt-Analyseklasse

DXFAnalyzer: Umfassende DXF/DWG-Analyse-Engine.
Data models are in analyzer_models.py.
Specialized analyzers (FloorPlan, TechnicalDrawing) are in
specialized_analyzers.py.
"""

import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Optional, Union

import ezdxf
from ezdxf.math import BoundingBox, Vec3

from .analyzer_models import (
    AnalysisReport,
    BlockInfo,
    DimensionInfo,
    ENTITY_CATEGORIES,
    EntityCategory,
    GeometryInfo,
    LayerInfo,
    TextInfo,
)


def load_cad_file(filepath):
    """
    Universelle Ladefunktion für DXF und DWG Dateien.

    Returns:
        Tuple (ezdxf.Drawing, was_converted: bool, original_format: str)
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    if suffix == ".dxf":
        doc = ezdxf.readfile(str(filepath))
        return doc, False, "DXF"

    elif suffix == ".dwg":
        try:
            from ezdxf.addons import odafc
            doc = odafc.readfile(str(filepath))
            return doc, True, "DWG"
        except ImportError:
            pass
        except Exception:
            pass

        from .dwg_converter import DWGConverterService
        converter = DWGConverterService()
        result = converter.convert(str(filepath))
        if result.success and result.dxf_path:
            doc = ezdxf.readfile(str(result.dxf_path))
            return doc, True, "DWG"

        raise RuntimeError(
            f"Kann DWG-Datei nicht laden: {filepath}\n"
            "ODA File Converter nicht gefunden."
        )

    else:
        raise ValueError(
            f"Nicht unterstuetztes Format: {suffix}"
        )

# ============================================================================
# HAUPT-ANALYSEKLASSE
# ============================================================================

class DXFAnalyzer:
    """
    Umfassende DXF/DWG-Analyse-Engine.
    
    Unterstützt sowohl DXF als auch DWG Dateien.
    DWG-Dateien werden automatisch via ODA File Converter konvertiert.
    
    Verwendung:
        analyzer = DXFAnalyzer("zeichnung.dxf")  # oder .dwg
        report = analyzer.full_analysis()
        analyzer.export_json("report.json")
    """
    
    def __init__(self, filepath: str | Path):
        """
        Initialisiert den Analyzer.
        
        Args:
            filepath: Pfad zur DXF- oder DWG-Datei
        """
        self.filepath = Path(filepath)
        
        # Lade Datei (DXF oder DWG)
        self.doc, self._was_converted, self._source_format = load_cad_file(filepath)
        self.msp = self.doc.modelspace()
        
        # Caches für Performance
        self._entity_cache: list = None
        self._layer_cache: dict = None
        self._block_cache: dict = None
    
    @property
    def source_format(self) -> str:
        """Gibt das Original-Format zurück (DXF oder DWG)."""
        return self._source_format
    
    @property
    def was_converted(self) -> bool:
        """Gibt zurück ob die Datei konvertiert wurde."""
        return self._was_converted
    
    # -------------------------------------------------------------------------
    # ENTITY-ANALYSE
    # -------------------------------------------------------------------------
    
    @property
    def entities(self) -> list:
        """Alle Entities (gecached)."""
        if self._entity_cache is None:
            self._entity_cache = list(self.msp)
        return self._entity_cache
    
    def count_entities(self) -> dict[str, int]:
        """Zählt Entities nach Typ."""
        return dict(Counter(e.dxftype() for e in self.entities))
    
    def count_by_category(self) -> dict[str, int]:
        """Zählt Entities nach Kategorie."""
        counts = Counter()
        for entity in self.entities:
            cat = ENTITY_CATEGORIES.get(entity.dxftype(), EntityCategory.OTHER)
            counts[cat.name] += 1
        return dict(counts)
    
    def get_entities_by_type(self, entity_type: str) -> Iterator:
        """Filtert Entities nach Typ."""
        return self.msp.query(entity_type)
    
    def get_entities_by_layer(self, layer_name: str) -> Iterator:
        """Filtert Entities nach Layer."""
        return self.msp.query(f"*[layer=='{layer_name}']")
    
    def get_entities_by_category(self, category: EntityCategory) -> list:
        """Filtert Entities nach Kategorie."""
        return [
            e for e in self.entities 
            if ENTITY_CATEGORIES.get(e.dxftype(), EntityCategory.OTHER) == category
        ]
    
    # -------------------------------------------------------------------------
    # LAYER-ANALYSE
    # -------------------------------------------------------------------------
    
    def analyze_layers(self) -> list[LayerInfo]:
        """Analysiert alle Layer."""
        if self._layer_cache is not None:
            return list(self._layer_cache.values())
        
        # Layer-Entity-Zuordnung
        layer_entities = defaultdict(lambda: {"count": 0, "types": Counter()})
        for entity in self.entities:
            layer = entity.dxf.layer
            layer_entities[layer]["count"] += 1
            layer_entities[layer]["types"][entity.dxftype()] += 1
        
        layers = []
        for layer in self.doc.layers:
            name = layer.dxf.name
            # Handle both property and method access for compatibility
            is_on = layer.is_on() if callable(layer.is_on) else layer.is_on
            is_frozen = layer.is_frozen() if callable(layer.is_frozen) else layer.is_frozen
            is_locked = layer.is_locked() if callable(layer.is_locked) else layer.is_locked
            
            info = LayerInfo(
                name=name,
                color=layer.dxf.color,
                linetype=layer.dxf.linetype,
                is_on=is_on,
                is_frozen=is_frozen,
                is_locked=is_locked,
                entity_count=layer_entities[name]["count"],
                entity_types=dict(layer_entities[name]["types"])
            )
            layers.append(info)
        
        self._layer_cache = {l.name: l for l in layers}
        return layers
    
    def get_layer_names(self) -> list[str]:
        """Liste aller Layer-Namen."""
        return [layer.dxf.name for layer in self.doc.layers]
    
    def get_empty_layers(self) -> list[str]:
        """Findet leere Layer."""
        layers = self.analyze_layers()
        return [l.name for l in layers if l.entity_count == 0]
    
    def get_layer_statistics(self) -> dict:
        """Statistiken über Layer."""
        layers = self.analyze_layers()
        return {
            "total": len(layers),
            "with_entities": sum(1 for l in layers if l.entity_count > 0),
            "empty": sum(1 for l in layers if l.entity_count == 0),
            "frozen": sum(1 for l in layers if l.is_frozen),
            "off": sum(1 for l in layers if not l.is_on),
        }
    
    # -------------------------------------------------------------------------
    # BLOCK-ANALYSE
    # -------------------------------------------------------------------------
    
    def analyze_blocks(self) -> list[BlockInfo]:
        """Analysiert alle Block-Definitionen und deren Verwendung."""
        if self._block_cache is not None:
            return list(self._block_cache.values())
        
        # INSERT-Referenzen zählen
        insert_counts = Counter()
        insert_positions = defaultdict(list)
        
        for insert in self.msp.query("INSERT"):
            name = insert.dxf.name
            insert_counts[name] += 1
            insert_positions[name].append(tuple(insert.dxf.insert))
        
        blocks = []
        for block in self.doc.blocks:
            if block.name.startswith("*"):  # Interne Blöcke überspringen
                continue
            
            # Attribute-Definitionen finden
            attdefs = list(block.query("ATTDEF"))
            attr_tags = [a.dxf.tag for a in attdefs]
            
            info = BlockInfo(
                name=block.name,
                base_point=tuple(block.base_point),
                entity_count=len(list(block)),
                has_attributes=len(attdefs) > 0,
                attribute_tags=attr_tags,
                insert_count=insert_counts.get(block.name, 0),
                insert_positions=insert_positions.get(block.name, [])
            )
            blocks.append(info)
        
        self._block_cache = {b.name: b for b in blocks}
        return blocks
    
    def get_block_inserts(self, block_name: str) -> list[dict]:
        """Alle INSERT-Referenzen eines Blocks mit Attributen."""
        inserts = []
        
        for insert in self.msp.query(f"INSERT[name=='{block_name}']"):
            attribs = {}
            if insert.has_attrib:
                for attrib in insert.attribs:
                    attribs[attrib.dxf.tag] = attrib.dxf.text
            
            inserts.append({
                "handle": insert.dxf.handle,
                "position": tuple(insert.dxf.insert),
                "rotation": insert.dxf.rotation,
                "scale": (insert.dxf.xscale, insert.dxf.yscale, insert.dxf.zscale),
                "layer": insert.dxf.layer,
                "attributes": attribs
            })
        
        return inserts
    
    def get_unused_blocks(self) -> list[str]:
        """Findet nicht verwendete Block-Definitionen."""
        blocks = self.analyze_blocks()
        return [b.name for b in blocks if b.insert_count == 0]
    
    # -------------------------------------------------------------------------
    # GEOMETRIE-ANALYSE
    # -------------------------------------------------------------------------
    
    def calculate_bounding_box(self) -> dict:
        """Berechnet die Bounding Box aller Entities."""
        bbox = BoundingBox()
        
        for entity in self.entities:
            try:
                # Verschiedene Entity-Typen haben unterschiedliche Vertex-Methoden
                if hasattr(entity, 'vertices'):
                    for v in entity.vertices():
                        bbox.extend([v])
                elif entity.dxftype() == "LINE":
                    bbox.extend([entity.dxf.start, entity.dxf.end])
                elif entity.dxftype() == "CIRCLE":
                    c = entity.dxf.center
                    r = entity.dxf.radius
                    bbox.extend([
                        Vec3(c.x - r, c.y - r, c.z),
                        Vec3(c.x + r, c.y + r, c.z)
                    ])
                elif entity.dxftype() == "ARC":
                    c = entity.dxf.center
                    r = entity.dxf.radius
                    bbox.extend([
                        Vec3(c.x - r, c.y - r, c.z),
                        Vec3(c.x + r, c.y + r, c.z)
                    ])
                elif entity.dxftype() == "POINT":
                    bbox.extend([entity.dxf.location])
                elif entity.dxftype() in ("TEXT", "MTEXT"):
                    bbox.extend([entity.dxf.insert])
                elif entity.dxftype() == "INSERT":
                    bbox.extend([entity.dxf.insert])
            except (AttributeError, TypeError):
                pass
        
        if bbox.has_data:
            return {
                "min": {"x": bbox.extmin.x, "y": bbox.extmin.y, "z": bbox.extmin.z},
                "max": {"x": bbox.extmax.x, "y": bbox.extmax.y, "z": bbox.extmax.z},
                "size": {
                    "width": bbox.extmax.x - bbox.extmin.x,
                    "height": bbox.extmax.y - bbox.extmin.y,
                    "depth": bbox.extmax.z - bbox.extmin.z,
                },
                "center": {
                    "x": (bbox.extmin.x + bbox.extmax.x) / 2,
                    "y": (bbox.extmin.y + bbox.extmax.y) / 2,
                    "z": (bbox.extmin.z + bbox.extmax.z) / 2,
                }
            }
        return None
    
    def extract_geometry(self, entity_types: list[str] = None) -> list[GeometryInfo]:
        """
        Extrahiert Geometrie-Daten aus Entities.
        
        Args:
            entity_types: Filter für Entity-Typen (None = alle)
        """
        geometries = []
        
        for entity in self.entities:
            etype = entity.dxftype()
            
            if entity_types and etype not in entity_types:
                continue
            
            geom_data = self._extract_entity_geometry(entity)
            if geom_data:
                geometries.append(GeometryInfo(
                    entity_type=etype,
                    layer=entity.dxf.layer,
                    color=entity.dxf.color,
                    handle=entity.dxf.handle,
                    geometry=geom_data
                ))
        
        return geometries
    
    def _extract_entity_geometry(self, entity) -> dict:
        """Extrahiert Geometrie-Daten einer einzelnen Entity."""
        etype = entity.dxftype()
        
        if etype == "LINE":
            return {
                "start": tuple(entity.dxf.start),
                "end": tuple(entity.dxf.end),
                "length": entity.dxf.start.distance(entity.dxf.end)
            }
        
        elif etype == "CIRCLE":
            return {
                "center": tuple(entity.dxf.center),
                "radius": entity.dxf.radius,
                "area": math.pi * entity.dxf.radius ** 2,
                "circumference": 2 * math.pi * entity.dxf.radius
            }
        
        elif etype == "ARC":
            return {
                "center": tuple(entity.dxf.center),
                "radius": entity.dxf.radius,
                "start_angle": entity.dxf.start_angle,
                "end_angle": entity.dxf.end_angle,
                "arc_length": self._calculate_arc_length(entity)
            }
        
        elif etype == "LWPOLYLINE":
            points = list(entity.get_points("xy"))
            return {
                "points": points,
                "closed": entity.closed,
                "vertex_count": len(points),
                "perimeter": self._calculate_polyline_length(points, entity.closed),
                "area": self._calculate_polygon_area(points) if entity.closed else None
            }
        
        elif etype == "POINT":
            return {"location": tuple(entity.dxf.location)}
        
        elif etype == "ELLIPSE":
            return {
                "center": tuple(entity.dxf.center),
                "major_axis": tuple(entity.dxf.major_axis),
                "ratio": entity.dxf.ratio,
                "start_param": entity.dxf.start_param,
                "end_param": entity.dxf.end_param
            }
        
        return None
    
    def _calculate_arc_length(self, arc) -> float:
        """Berechnet die Bogenlänge eines ARC."""
        angle = abs(arc.dxf.end_angle - arc.dxf.start_angle)
        if angle > 180:
            angle = 360 - angle
        return math.radians(angle) * arc.dxf.radius
    
    def _calculate_polyline_length(self, points: list, closed: bool) -> float:
        """Berechnet die Länge einer Polylinie."""
        length = 0.0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            length += math.sqrt(dx*dx + dy*dy)
        
        if closed and len(points) > 2:
            dx = points[0][0] - points[-1][0]
            dy = points[0][1] - points[-1][1]
            length += math.sqrt(dx*dx + dy*dy)
        
        return length
    
    def _calculate_polygon_area(self, points: list) -> float:
        """Berechnet die Fläche eines Polygons (Shoelace-Formel)."""
        n = len(points)
        if n < 3:
            return 0.0
        
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    # -------------------------------------------------------------------------
    # TEXT-EXTRAKTION
    # -------------------------------------------------------------------------
    
    def extract_texts(self) -> list[TextInfo]:
        """Extrahiert alle Texte aus der Zeichnung."""
        texts = []
        
        for entity in self.msp.query("TEXT MTEXT"):
            etype = entity.dxftype()
            
            if etype == "TEXT":
                texts.append(TextInfo(
                    content=entity.dxf.text,
                    position=tuple(entity.dxf.insert),
                    height=entity.dxf.height,
                    rotation=entity.dxf.rotation,
                    layer=entity.dxf.layer,
                    entity_type="TEXT",
                    style=entity.dxf.style
                ))
            else:  # MTEXT
                texts.append(TextInfo(
                    content=entity.text,  # Bereinigter Text
                    position=tuple(entity.dxf.insert),
                    height=entity.dxf.char_height,
                    rotation=entity.dxf.rotation,
                    layer=entity.dxf.layer,
                    entity_type="MTEXT",
                    style=entity.dxf.style
                ))
        
        return texts
    
    def extract_block_attributes(self) -> list[dict]:
        """Extrahiert alle Block-Attribute (ATTRIB)."""
        attributes = []
        
        for insert in self.msp.query("INSERT"):
            if insert.has_attrib:
                block_attribs = {
                    "block_name": insert.dxf.name,
                    "position": tuple(insert.dxf.insert),
                    "layer": insert.dxf.layer,
                    "attributes": {}
                }
                for attrib in insert.attribs:
                    block_attribs["attributes"][attrib.dxf.tag] = attrib.dxf.text
                
                attributes.append(block_attribs)
        
        return attributes
    
    # -------------------------------------------------------------------------
    # BEMAÄUNGS-EXTRAKTION
    # -------------------------------------------------------------------------
    
    def extract_dimensions(self) -> list[DimensionInfo]:
        """Extrahiert alle Bemaßungen."""
        dimensions = []
        
        for dim in self.msp.query("DIMENSION"):
            try:
                measurement = dim.get_measurement()
            except:
                measurement = None
            
            dimensions.append(DimensionInfo(
                measurement=measurement,
                text_override=dim.dxf.text if dim.dxf.text else "",
                dim_type=str(dim.dimtype),
                layer=dim.dxf.layer,
                definition_points=[
                    tuple(dim.dxf.defpoint),
                    tuple(dim.dxf.defpoint2) if hasattr(dim.dxf, 'defpoint2') else None,
                    tuple(dim.dxf.defpoint3) if hasattr(dim.dxf, 'defpoint3') else None,
                ]
            ))
        
        return dimensions
    
    def get_dimension_values(self) -> list[float]:
        """Liste aller Bemaßungswerte."""
        dims = self.extract_dimensions()
        return [d.measurement for d in dims if d.measurement is not None]
    
    # -------------------------------------------------------------------------
    # QUALITÄTSPRÜFUNG
    # -------------------------------------------------------------------------
    
    def check_quality(self) -> list[dict]:
        """Führt Qualitätsprüfungen durch."""
        issues = []
        
        # 1. Sehr kurze Linien
        for line in self.msp.query("LINE"):
            length = line.dxf.start.distance(line.dxf.end)
            if length < 0.1:
                issues.append({
                    "type": "SHORT_LINE",
                    "severity": "info",
                    "handle": line.dxf.handle,
                    "message": f"Sehr kurze Linie ({length:.4f})",
                    "layer": line.dxf.layer
                })
        
        # 2. Entities auf Layer "0"
        layer0_count = sum(1 for e in self.entities if e.dxf.layer == "0")
        if layer0_count > 0:
            issues.append({
                "type": "LAYER_ZERO",
                "severity": "info",
                "message": f"{layer0_count} Entities auf Layer '0'",
            })
        
        # 3. Leere Layer
        empty_layers = self.get_empty_layers()
        if empty_layers:
            issues.append({
                "type": "EMPTY_LAYERS",
                "severity": "info",
                "message": f"{len(empty_layers)} leere Layer",
                "layers": empty_layers
            })
        
        # 4. Unbenutzte Blöcke
        unused_blocks = self.get_unused_blocks()
        if unused_blocks:
            issues.append({
                "type": "UNUSED_BLOCKS",
                "severity": "info",
                "message": f"{len(unused_blocks)} unbenutzte Block-Definitionen",
                "blocks": unused_blocks
            })
        
        # 5. Doppelte Entities (gleiche Geometrie)
        duplicates = self._find_duplicate_entities()
        if duplicates:
            issues.append({
                "type": "DUPLICATES",
                "severity": "warning",
                "message": f"{len(duplicates)} mögliche Duplikate gefunden",
                "count": len(duplicates)
            })
        
        # 6. Nicht geschlossene Polylinien (die es sein sollten)
        open_polylines = self._find_nearly_closed_polylines()
        if open_polylines:
            issues.append({
                "type": "UNCLOSED_POLYLINES",
                "severity": "warning",
                "message": f"{len(open_polylines)} fast geschlossene Polylinien",
                "handles": open_polylines
            })
        
        return issues
    
    def _find_duplicate_entities(self, tolerance: float = 0.001) -> list[tuple]:
        """Findet potenzielle Duplikate."""
        duplicates = []
        lines = list(self.msp.query("LINE"))
        
        for i, line1 in enumerate(lines):
            for line2 in lines[i+1:]:
                if (line1.dxf.start.distance(line2.dxf.start) < tolerance and
                    line1.dxf.end.distance(line2.dxf.end) < tolerance):
                    duplicates.append((line1.dxf.handle, line2.dxf.handle))
        
        return duplicates
    
    def _find_nearly_closed_polylines(self, tolerance: float = 1.0) -> list[str]:
        """Findet Polylinien die fast geschlossen sind."""
        nearly_closed = []
        
        for pline in self.msp.query("LWPOLYLINE"):
            if not pline.closed:
                points = list(pline.get_points("xy"))
                if len(points) >= 3:
                    first = points[0]
                    last = points[-1]
                    dist = math.sqrt((first[0]-last[0])**2 + (first[1]-last[1])**2)
                    if dist < tolerance:
                        nearly_closed.append(pline.dxf.handle)
        
        return nearly_closed
    
    # -------------------------------------------------------------------------
    # VOLLSTÄNDIGE ANALYSE
    # -------------------------------------------------------------------------
    
    def full_analysis(self) -> AnalysisReport:
        """Führt eine vollständige Analyse durch."""
        bbox = self.calculate_bounding_box()
        
        # Geschätzte Fläche (2D)
        estimated_area = 0.0
        if bbox:
            estimated_area = bbox["size"]["width"] * bbox["size"]["height"]
        
        # Einheiten aus Header
        units_map = {
            0: "Unitless", 1: "Inches", 2: "Feet", 3: "Miles",
            4: "Millimeters", 5: "Centimeters", 6: "Meters", 7: "Kilometers"
        }
        try:
            insunits = self.doc.header.get("$INSUNITS", 0)
            units = units_map.get(insunits, "Unknown")
        except:
            units = "Unknown"
        
        return AnalysisReport(
            filename=self.filepath.name,
            dxf_version=self.doc.dxfversion,
            encoding=self.doc.encoding,
            units=units,
            total_entities=len(self.entities),
            entity_statistics=self.count_entities(),
            category_statistics=self.count_by_category(),
            layers=[asdict(l) for l in self.analyze_layers()],
            blocks=[asdict(b) for b in self.analyze_blocks()],
            bounding_box=bbox,
            estimated_area=estimated_area,
            texts=[asdict(t) for t in self.extract_texts()],
            dimensions=[asdict(d) for d in self.extract_dimensions()],
            issues=self.check_quality(),
            source_format=self._source_format,
            was_converted=self._was_converted
        )
    
    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------
    
    def export_json(self, filepath: str, indent: int = 2):
        """Exportiert vollständige Analyse als JSON."""
        report = self.full_analysis()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=indent, default=str, ensure_ascii=False)
        
        return filepath
    
    def export_entities_csv(self, filepath: str):
        """Exportiert Entity-Geometrie als CSV."""
        import csv
        
        geometries = self.extract_geometry(["LINE", "CIRCLE", "ARC", "LWPOLYLINE"])
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["handle", "type", "layer", "color", "geometry"])
            
            for geom in geometries:
                writer.writerow([
                    geom.handle,
                    geom.entity_type,
                    geom.layer,
                    geom.color,
                    json.dumps(geom.geometry)
                ])
        
        return filepath
    
    def export_texts_csv(self, filepath: str):
        """Exportiert Texte als CSV."""
        import csv
        
        texts = self.extract_texts()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["content", "position_x", "position_y", "height", 
                           "rotation", "layer", "type"])
            
            for text in texts:
                writer.writerow([
                    text.content,
                    text.position[0],
                    text.position[1],
                    text.height,
                    text.rotation,
                    text.layer,
                    text.entity_type
                ])
        
        return filepath

