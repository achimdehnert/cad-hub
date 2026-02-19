"""
MCP Bridge Data Models

Enums and dataclasses for CAD MCP Bridge results.
"""
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class CADFormat(StrEnum):
    """Unterstützte CAD-Formate"""
    IFC = "ifc"
    DXF = "dxf"
    DWG = "dwg"
    IGES = "iges"
    FBX = "fbx"
    GLTF = "gltf"
    GLB = "glb"
    THREE_MF = "3mf"
    PLY = "ply"
    STEP = "step"
    UNKNOWN = "unknown"


@dataclass
class AnalysisResult:
    """Ergebnis einer CAD-Analyse"""
    success: bool
    file_path: str
    format: CADFormat
    data: dict[str, Any] = field(default_factory=dict)
    markdown_report: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "format": self.format.value,
            "data": self.data,
            "markdown_report": self.markdown_report,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class DXFQualityResult:
    """Ergebnis der DXF-Qualitätsprüfung"""
    success: bool
    file_path: str
    dimension_chains: dict[str, Any] = field(default_factory=dict)
    section_views: dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NLQueryResult:
    """Ergebnis einer Natural Language Abfrage"""
    success: bool
    query: str
    answer: str
    data: Any = None
    source_file: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchResult:
    """Ergebnis einer Batch-Analyse"""
    success: bool
    total_files: int
    analyzed: int
    failed: int
    results: list[AnalysisResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "total_files": self.total_files,
            "analyzed": self.analyzed,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }


