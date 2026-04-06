"""
compat shim: ifc_parser_models -> nl2cad.core.models.ifc

Diese Datei existiert nur für Backward-Kompatibilität.
Neu-Code soll direkt nl2cad.core.models.ifc importieren.
"""

from nl2cad.core.models.ifc import (
    IFCDoor,
    IFCFloor,
    IFCModel,
    IFCRoom,
    IFCSlab,
    IFCWall,
    IFCWindow,
)

__all__ = [
    "IFCDoor",
    "IFCFloor",
    "IFCModel",
    "IFCRoom",
    "IFCSlab",
    "IFCWall",
    "IFCWindow",
]
