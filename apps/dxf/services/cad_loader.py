"""
CAD Loader Service - Unified interface for DXF/DWG loading, rendering and analysis.

Combines:
- DXFAnalyzer (from toolkit) - Full analysis capabilities
- DXFRendererService - SVG/PNG/JSON rendering for viewers
- DWGConverter - Automatic DWG→DXF conversion
"""

import logging
import tempfile
from dataclasses import asdict
from pathlib import Path

from nl2cad.core.config import DXFParserConfig
from nl2cad.core.models.dxf import DXFModel
from nl2cad.core.parsers.dxf_parser import DXFParser

from .analyzer.analyzer_models import AnalysisReport
from .analyzer.dwg_converter import DWGConverterService as DWGConverter
from .analyzer.dxf_analyzer import DXFAnalyzer
from .analyzer.dxf_renderer import DXFRendererService
from .analyzer.specialized_analyzers import FloorPlanAnalyzer, TechnicalDrawingAnalyzer

logger = logging.getLogger(__name__)

# Layer-Keywords, die cad-hub bisher zusätzlich zu nl2cads
# DXFParserConfig.excluded_layer_keywords-Default ausschloss (Bauteil-Layer wie
# Wand/Dach/Treppe, die nl2cads AEC-neutraler Default nicht kennt). Union statt
# Ersetzen, sonst gehen nl2cads eigene Defaults (u.a. "sanitary", "scale",
# "note") verloren — Parität geprüft bei der ADR-012-T2-Migration.
_CADHUB_EXTRA_EXCLUDED_LAYER_KEYWORDS = frozenset(
    {
        "decken",
        "ceiling",
        "deckenkonstruktion",
        "fußbodenaufbau",
        "wand",
        "wände",
        "wall",
        "konstruktion",
        "tragwerk",
        "fundament",
        "dach",
        "roof",
        "fassade",
        "treppe",
        "stair",
        "aufzug",
        "elevator",
    }
)


class CADLoaderService:
    """
    Unified CAD loading service with analysis and rendering capabilities.

    Automatically handles:
    - DXF files (native support)
    - DWG files (automatic conversion via ODA)

    Usage:
        # From file path
        loader = CADLoaderService.from_file("drawing.dxf")

        # From uploaded bytes
        loader = CADLoaderService.from_bytes(content, "drawing.dxf")

        # Get viewer data for Three.js
        viewer_data = loader.get_viewer_data()

        # Get full analysis
        analysis = loader.get_analysis()

        # Get SVG thumbnail
        svg = loader.get_thumbnail()
    """

    def __init__(self, filepath: str | Path):
        """
        Initialize loader with a file path.

        Args:
            filepath: Path to DXF or DWG file
        """
        self.filepath = Path(filepath)
        self._analyzer: DXFAnalyzer | None = None
        self._renderer: DXFRendererService | None = None
        self._floor_analyzer: FloorPlanAnalyzer | None = None
        self._tech_analyzer: TechnicalDrawingAnalyzer | None = None
        self._dxf_model: DXFModel | None = None
        self._resolved_dxf_path: Path | None = None

    @classmethod
    def from_file(cls, filepath: str | Path) -> "CADLoaderService":
        """Create loader from file path."""
        return cls(filepath)

    @classmethod
    def from_bytes(cls, content: bytes, filename: str = "upload.dxf") -> "CADLoaderService":
        """
        Create loader from file content bytes.

        Args:
            content: File content as bytes
            filename: Original filename (for format detection)
        """
        # Write to temp file
        suffix = Path(filename).suffix.lower() or ".dxf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        loader = cls(temp_path)
        loader._is_temp = True
        loader._original_filename = filename
        return loader

    @property
    def analyzer(self) -> DXFAnalyzer:
        """Get or create analyzer instance (lazy loading)."""
        if self._analyzer is None:
            self._analyzer = DXFAnalyzer(self.filepath)
        return self._analyzer

    @property
    def renderer(self) -> DXFRendererService:
        """Get or create renderer instance (lazy loading)."""
        if self._renderer is None:
            self._renderer = DXFRendererService()
            self._renderer.load_file(self.filepath)
        return self._renderer

    @property
    def floor_analyzer(self) -> FloorPlanAnalyzer:
        """Get floor plan analyzer (lazy loading)."""
        if self._floor_analyzer is None:
            self._floor_analyzer = FloorPlanAnalyzer(self.filepath)
        return self._floor_analyzer

    @property
    def tech_analyzer(self) -> TechnicalDrawingAnalyzer:
        """Get technical drawing analyzer (lazy loading)."""
        if self._tech_analyzer is None:
            self._tech_analyzer = TechnicalDrawingAnalyzer(self.filepath)
        return self._tech_analyzer

    def _resolve_dxf_path(self) -> Path:
        """
        Resolve self.filepath to a real .dxf file, converting DWG if needed.

        DXFParser.parse() only reads .dxf files. DWG conversion here is
        independent of DXFAnalyzer's own conversion (self.analyzer) — this
        causes a second ODA pass for DWG uploads; acceptable for now, a
        shared conversion cache is a separate fast-follow.
        """
        if self.filepath.suffix.lower() == ".dxf":
            return self.filepath
        if self._resolved_dxf_path is None:
            result = DWGConverter().convert_to_dxf(self.filepath)
            if not result.success or not result.dxf_path:
                raise RuntimeError(
                    f"DWG→DXF Konvertierung fehlgeschlagen: {self.filepath} ({result.error})"
                )
            self._resolved_dxf_path = result.dxf_path
        return self._resolved_dxf_path

    @property
    def dxf_model(self) -> DXFModel:
        """Get or create nl2cad DXFModel (lazy loading, cached per instance)."""
        if self._dxf_model is None:
            default_config = DXFParserConfig()
            config = DXFParserConfig(
                read_all_entities=False,
                excluded_layer_keywords=default_config.excluded_layer_keywords
                | _CADHUB_EXTRA_EXCLUDED_LAYER_KEYWORDS,
            )
            self._dxf_model = DXFParser(config=config).parse(self._resolve_dxf_path())
        return self._dxf_model

    # -------------------------------------------------------------------------
    # VIEWER DATA
    # -------------------------------------------------------------------------

    def get_viewer_data(self) -> dict:
        """
        Get data optimized for Three.js viewer.

        Returns:
            dict with grouped entities, layers, bounds, stats
        """
        return self.renderer.export_for_threejs()

    def get_thumbnail(self, max_size: int = 300) -> str | None:
        """
        Get SVG thumbnail.

        Args:
            max_size: Maximum dimension in pixels

        Returns:
            SVG string or None
        """
        return self.renderer.get_thumbnail_svg(max_size)

    def render_svg(self, width: int = 800, height: int = 600) -> str | None:
        """Render full SVG."""
        return self.renderer.render_to_svg(width=width, height=height)

    # -------------------------------------------------------------------------
    # ANALYSIS
    # -------------------------------------------------------------------------

    def get_analysis(self) -> AnalysisReport:
        """
        Get full analysis report.

        Returns:
            AnalysisReport dataclass with all analysis data
        """
        return self.analyzer.full_analysis()

    def get_analysis_dict(self) -> dict:
        """Get analysis as dictionary (JSON-serializable)."""
        report = self.get_analysis()
        return asdict(report)

    def get_statistics(self) -> dict:
        """Get quick statistics."""
        return {
            "total_entities": len(self.analyzer.entities),
            "entity_counts": self.analyzer.count_entities(),
            "category_counts": self.analyzer.count_by_category(),
            "layer_count": len(self.analyzer.get_layer_names()),
            "bounding_box": self.analyzer.calculate_bounding_box(),
        }

    def get_layers(self) -> list[dict]:
        """Get layer information."""
        layers = self.analyzer.analyze_layers()
        return [asdict(l) for l in layers]

    def get_blocks(self) -> list[dict]:
        """Get block information."""
        blocks = self.analyzer.analyze_blocks()
        return [asdict(b) for b in blocks]

    def get_texts(self) -> list[dict]:
        """Get all texts."""
        texts = self.analyzer.extract_texts()
        return [asdict(t) for t in texts]

    def get_dimensions(self) -> list[dict]:
        """Get all dimensions."""
        dims = self.analyzer.extract_dimensions()
        return [asdict(d) for d in dims]

    def check_quality(self) -> list[dict]:
        """Run quality checks."""
        return self.analyzer.check_quality()

    # -------------------------------------------------------------------------
    # FLOOR PLAN ANALYSIS
    # -------------------------------------------------------------------------

    def get_rooms(self) -> list[dict]:
        """
        Identify rooms in floor plan.

        Sourced from nl2cad-core DXFParser (ADR-012 T2) — polygon-based
        extraction + text-label matching, not the old pure text-keyword scan.
        Same order as get_room_areas(): both read self.dxf_model.rooms, so
        index i in one corresponds to index i in the other.
        """
        return [
            {
                "name": room.name,
                "position": {"x": room.position.x, "y": room.position.y},
                "layer": room.layer,
            }
            for room in self.dxf_model.rooms
        ]

    def get_room_areas(self) -> list[dict]:
        """
        Room areas in real m²/m (unit-corrected by nl2cad-core), not raw DXF units.
        """
        return [
            {
                "handle": "",
                "layer": room.layer,
                "area": room.area_m2,
                "perimeter": room.perimeter_m,
                "vertex_count": len(room.vertices),
            }
            for room in self.dxf_model.rooms
        ]

    def get_doors(self) -> list[dict]:
        """Find door blocks."""
        return self.floor_analyzer.find_doors()

    def get_windows(self) -> list[dict]:
        """Find window blocks."""
        return self.floor_analyzer.find_windows()

    def get_furniture(self) -> list[dict]:
        """Find furniture blocks."""
        return self.floor_analyzer.find_furniture()

    def get_sanitary(self) -> list[dict]:
        """Find sanitary equipment blocks."""
        return self.floor_analyzer.find_sanitary()

    # -------------------------------------------------------------------------
    # TECHNICAL DRAWING ANALYSIS
    # -------------------------------------------------------------------------

    def get_holes(self) -> list[dict]:
        """Extract holes/circles from technical drawing."""
        return self.tech_analyzer.extract_holes()

    def get_tolerances(self) -> list[dict]:
        """Extract tolerance information."""
        return self.tech_analyzer.extract_tolerances()

    def get_centerlines(self) -> list[dict]:
        """Find centerlines."""
        return self.tech_analyzer.analyze_centerlines()

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def export_json(self, filepath: str) -> str:
        """Export full analysis to JSON file."""
        return self.analyzer.export_json(filepath)

    def export_texts_csv(self, filepath: str) -> str:
        """Export texts to CSV."""
        return self.analyzer.export_texts_csv(filepath)

    def export_entities_csv(self, filepath: str) -> str:
        """Export entities to CSV."""
        return self.analyzer.export_entities_csv(filepath)

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------

    @property
    def source_format(self) -> str:
        """Get original file format (DXF or DWG)."""
        return self.analyzer.source_format

    @property
    def was_converted(self) -> bool:
        """Check if file was converted from DWG."""
        return self.analyzer.was_converted

    @property
    def filename(self) -> str:
        """Get filename."""
        if hasattr(self, "_original_filename"):
            return self._original_filename
        return self.filepath.name

    def cleanup(self):
        """Clean up temporary files."""
        if hasattr(self, "_is_temp") and self._is_temp:
            try:
                self.filepath.unlink(missing_ok=True)
            except Exception:
                pass

    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()


# Convenience functions
def load_and_analyze(filepath: str | Path) -> dict:
    """Quick function to load and analyze a CAD file."""
    loader = CADLoaderService.from_file(filepath)
    return loader.get_analysis_dict()


def get_dwg_converter_status() -> dict:
    """Check DWG converter availability."""
    converter = DWGConverter()
    return converter.get_status()
