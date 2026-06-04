"""
Brandschutz data models.

Kern-Domänenobjekte werden aus nl2cad.brandschutz.models re-exportiert.
Symbol- und Report-Modelle (cad-hub-spezifisch) verbleiben hier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

try:
    from nl2cad.brandschutz.models import (
        Brandabschnitt,
        BrandschutzAnalyse,
        Brandschutzeinrichtung,
        BrandschutzKategorie,
        ExBereich,
        ExZone,
        Fluchtweg,
    )
except ImportError:
    # nl2cad-brandschutz deprecated — provide minimal stubs
    Brandabschnitt = None
    BrandschutzAnalyse = None
    BrandschutzKategorie = None
    Brandschutzeinrichtung = None
    ExBereich = None
    ExZone = None
    Fluchtweg = None

__all__ = [
    "Brandabschnitt",
    "BrandschutzAnalyse",
    "BrandschutzKategorie",
    "Brandschutzeinrichtung",
    "ExBereich",
    "ExZone",
    "Fluchtweg",
    "Feuerwiderstand",
    "SymbolTyp",
    "PlatzierungsRegel",
    "SymbolPlatzierung",
    "SymbolInsertionResult",
    "BerichtKonfiguration",
]


class Feuerwiderstand(Enum):
    """Feuerwiderstandsklassen nach DIN 4102 / EN 13501."""

    F30 = "F30"
    F60 = "F60"
    F90 = "F90"
    F120 = "F120"
    F180 = "F180"
    UNBEKANNT = "unbekannt"


# ============================================================
# Symbol Models (cad-hub-spezifisch, nicht in nl2cad)
# ============================================================


class SymbolTyp(Enum):
    """Brandschutz-Symboltypen nach DIN EN ISO 7010."""

    NOTAUSGANG = "E001"
    NOTAUSGANG_LINKS = "E001-L"
    NOTAUSGANG_RECHTS = "E001-R"
    SAMMELSTELLE = "E007"
    ERSTE_HILFE = "E003"
    FEUERLOESCHER = "F001"
    LOESCHDECKE = "F002"
    FEUERLEITER = "F003"
    BRANDMELDER = "F005"
    WANDHYDRANT = "F002"
    WARNUNG_FEUER = "W021"
    WARNUNG_EX = "W021"
    RAUCHMELDER = "RM"
    SPRINKLER = "SP"
    RWA = "RWA"
    FLUCHTWEG_PFEIL = "FW"


@dataclass
class PlatzierungsRegel:
    """Regel für Symbol-Platzierung."""

    symbol_typ: SymbolTyp
    max_abstand_m: float = 0.0
    max_flaeche_m2: float = 0.0
    min_anzahl: int = 0
    an_tueren: bool = False
    an_fluchtwegen: bool = False
    an_richtungswechsel: bool = False
    regelwerk: str = ""


@dataclass
class SymbolPlatzierung:
    """Vorgeschlagene Symbol-Platzierung."""

    symbol_typ: str
    position_x: float
    position_y: float
    rotation: float = 0.0
    layer: str = "Brandschutz_Symbole"
    begruendung: str = ""
    prioritaet: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SymbolInsertionResult:
    """Ergebnis der Symbol-Analyse und -Einfügung."""

    vorgeschlagene_symbole: list[SymbolPlatzierung] = field(default_factory=list)
    eingefuegte_symbole: list[SymbolPlatzierung] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    feuerloescher_fehlen: int = 0
    rauchmelder_fehlen: int = 0
    fluchtweg_schilder_fehlen: int = 0

    def to_dict(self) -> dict:
        return {
            "vorgeschlagene_symbole": [s.to_dict() for s in self.vorgeschlagene_symbole],
            "eingefuegte_symbole": [s.to_dict() for s in self.eingefuegte_symbole],
            "warnungen": self.warnungen,
            "statistik": {
                "feuerloescher_fehlen": self.feuerloescher_fehlen,
                "rauchmelder_fehlen": self.rauchmelder_fehlen,
                "fluchtweg_schilder_fehlen": self.fluchtweg_schilder_fehlen,
                "gesamt_vorgeschlagen": len(self.vorgeschlagene_symbole),
                "gesamt_eingefuegt": len(self.eingefuegte_symbole),
            },
        }


class BerichtKonfiguration:
    """Konfiguration für Berichtserstellung."""

    titel: str = "Brandschutz-Prüfbericht"
    projekt_name: str = ""
    etage: str = ""
    pruefer: str = ""
    datum: str = ""
    mit_zusammenfassung: bool = True
    mit_maengelliste: bool = True
    mit_symboluebersicht: bool = True
    mit_fluchtweganalyse: bool = True
    mit_regelwerkreferenzen: bool = True
    mit_empfehlungen: bool = True
    mit_grafiken: bool = True
    format: str = "pdf"
