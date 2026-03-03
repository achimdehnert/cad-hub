"""
Brandschutz Handler für CAD-Analyse.

Delegiert an nl2cad.brandschutz.analyzer.BrandschutzAnalyzer.
Hält die bisherige Handler-API (execute + input_data dict) für
Backward-Kompatibilität mit bestehenden cad-hub Views.

Regelwerke (via nl2cad):
- ASR A2.3 (Fluchtwege)
- DIN 4102 / EN 13501 (Feuerwiderstand)
- ATEX / BetrSichV (Ex-Schutz)
- DIN 14675 (Brandmeldeanlagen)
"""
from __future__ import annotations

import logging

from nl2cad.brandschutz.analyzer import BrandschutzAnalyzer
from nl2cad.brandschutz.models import BrandschutzAnalyse

from apps.core.handlers.base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


class BrandschutzHandler(BaseCADHandler):
    """
    Handler für Brandschutz-Analyse aus CAD-Dateien.

    Delegiert die eigentliche Analyse an nl2cad.brandschutz.BrandschutzAnalyzer.

    Input:
        loader: ezdxf-Dokument (für format="dxf") oder ifcopenshell IFCModel
        format: "dxf" oder "ifc"
        etage: Etagenbezeichnung (default: "EG")

    Output:
        brandschutz: BrandschutzAnalyse.to_dict()
        hat_kritische_maengel: bool
        fluchtwege_count, brandabschnitte_count, ex_bereiche_count, einrichtungen_count
    """

    name = "BrandschutzHandler"
    description = "Analysiert Brandschutz-Elemente in CAD-Dateien (via nl2cad-brandschutz)"
    required_inputs = ["loader", "format"]
    optional_inputs = ["etage"]

    def __init__(self) -> None:
        super().__init__()
        self._analyzer = BrandschutzAnalyzer()

    def execute(self, input_data: dict) -> CADHandlerResult:
        """Führt Brandschutz-Analyse durch."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )

        loader = input_data.get("loader")
        format_type = input_data.get("format", "dxf")
        etage = input_data.get("etage", "EG")

        if not loader:
            result.add_error("Kein CAD-Dokument (loader) übergeben")
            return result

        try:
            analyse: BrandschutzAnalyse
            if format_type == "dxf":
                analyse = self._analyzer.analyze_dxf(loader, etage=etage)
            elif format_type == "ifc":
                analyse = self._analyzer.analyze_ifc(loader)
            else:
                result.add_error(f"Unbekanntes Format: {format_type}")
                return result
        except Exception as e:
            result.add_error(f"Analyse-Fehler: {e}")
            logger.exception("[%s] Fehler bei Brandschutz-Analyse", self.name)
            return result

        result.data["brandschutz"] = analyse.to_dict()
        result.data["hat_kritische_maengel"] = analyse.hat_kritische_maengel
        result.data["fluchtwege_count"] = len(analyse.fluchtwege)
        result.data["brandabschnitte_count"] = len(analyse.brandabschnitte)
        result.data["ex_bereiche_count"] = len(analyse.ex_bereiche)
        result.data["einrichtungen_count"] = len(analyse.einrichtungen)
        result.data["warnungen"] = analyse.warnungen
        result.data["maengel"] = [
            {"schwere": m.schwere.value, "beschreibung": m.beschreibung, "regelwerk": m.regelwerk}
            for m in analyse.maengel
        ]

        result.status = HandlerStatus.SUCCESS
        logger.info(
            "[%s] %d Fluchtwege, %d Brandabschnitte, %d Mängel",
            self.name,
            len(analyse.fluchtwege),
            len(analyse.brandabschnitte),
            len(analyse.maengel),
        )
        return result


_brandschutz_handler: BrandschutzHandler | None = None


def get_brandschutz_handler() -> BrandschutzHandler:
    """Gibt BrandschutzHandler-Instanz zurück."""
    global _brandschutz_handler
    if _brandschutz_handler is None:
        _brandschutz_handler = BrandschutzHandler()
    return _brandschutz_handler
