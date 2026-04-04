"""
compat shim: IFCParserService -> nl2cad.core.parsers.IFCParser

Diese Datei existiert nur für Backward-Kompatibilität mit altem Code.
Neu-Code soll direkt nl2cad.core.parsers.IFCParser verwenden.
"""
from __future__ import annotations

import logging
from pathlib import Path

from nl2cad.core.exceptions import IFCParseError
from nl2cad.core.models.ifc import IFCModel
from nl2cad.core.parsers.ifc_parser import IFCParser

logger = logging.getLogger(__name__)


class IFCParserService:
    """
    Compat-Shim. Delegiert an nl2cad.core.parsers.IFCParser.

    Felder der alten ParsedRoom/ParsedWall/etc. sind durch IFCRoom/IFCWall/etc.
    ersetzt. Verwende tasks.py als Referenz-Implementierung für den Umstieg.
    """

    def __init__(self) -> None:
        self._parser = IFCParser()

    def parse_file(self, file_path: Path) -> IFCModel:
        """Parst IFC-Datei. Gibt IFCModel zurück (nicht mehr IFCParseResult)."""
        try:
            return self._parser.parse(file_path)
        except IFCParseError as e:
            logger.error("[IFCParserService] %s", e)
            raise
