"""Brandschutz data models: enums and dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ============================================================
# Brandschutz Analysis Models
# ============================================================


class Feuerwiderstand(Enum):
    """Feuerwiderstandsklassen nach DIN 4102 / EN 13501."""
    F30 = "F30"    # 30 Minuten
    F60 = "F60"    # 60 Minuten
    F90 = "F90"    # 90 Minuten
    F120 = "F120"  # 120 Minuten
    F180 = "F180"  # 180 Minuten
    UNBEKANNT = "unbekannt"


class ExZone(Enum):
    """Explosionsgefährdete Bereiche nach ATEX."""
    ZONE_0 = "Zone 0"    # Ständig explosionsfähige Atmosphäre (Gas)
    ZONE_1 = "Zone 1"    # Gelegentlich (Gas)
    ZONE_2 = "Zone 2"    # Selten und kurzzeitig (Gas)
    ZONE_20 = "Zone 20"  # Ständig (Staub)
    ZONE_21 = "Zone 21"  # Gelegentlich (Staub)
    ZONE_22 = "Zone 22"  # Selten (Staub)
    KEINE = "keine"


class BrandschutzKategorie(Enum):
    """Kategorien für Brandschutz-Elemente."""
    FLUCHTWEG = "fluchtweg"
    NOTAUSGANG = "notausgang"
    BRANDABSCHNITT = "brandabschnitt"
    BRANDWAND = "brandwand"
    BRANDSCHUTZTUR = "brandschutztür"
    FEUERLOESCHER = "feuerlöscher"
    HYDRANT = "hydrant"
    SPRINKLER = "sprinkler"
    RAUCHMELDER = "rauchmelder"
    WAERMEMELDER = "wärmemelder"
    BRANDMELDER = "brandmelder"
    RWA = "rwa"
    EX_ZONE = "ex_zone"
    LAGERBEREICH = "lagerbereich"
    SAMMELPLATZ = "sammelplatz"
    SONSTIGES = "sonstiges"


@dataclass
class Fluchtweg:
    """Fluchtweg-Information."""
    name: str = ""
    laenge_m: float = 0.0
    breite_m: float = 0.0
    layer: str = ""
    etage: str = ""
    ist_hauptfluchtweg: bool = False
    max_laenge_ok: bool = True  # Max 35m nach ASR A2.3
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Brandabschnitt:
    """Brandabschnitt-Information."""
    name: str = ""
    flaeche_m2: float = 0.0
    feuerwiderstand: str = Feuerwiderstand.UNBEKANNT.value
    layer: str = ""
    etage: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExBereich:
    """Explosionsgefährdeter Bereich."""
    name: str = ""
    zone: str = ExZone.KEINE.value
    flaeche_m2: float = 0.0
    layer: str = ""
    medium: str = ""  # Gas, Staub, etc.
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Brandschutzeinrichtung:
    """Brandschutz-Einrichtung (Melder, Löscher, etc.)."""
    typ: str = ""
    kategorie: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    layer: str = ""
    etage: str = ""
    block_name: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BrandschutzAnalyse:
    """Gesamtergebnis der Brandschutz-Analyse."""
    fluchtwege: list[Fluchtweg] = field(default_factory=list)
    brandabschnitte: list[Brandabschnitt] = field(default_factory=list)
    ex_bereiche: list[ExBereich] = field(default_factory=list)
    einrichtungen: list[Brandschutzeinrichtung] = field(default_factory=list)
    
    # Zusammenfassung
    anzahl_notausgaenge: int = 0
    anzahl_feuerloescher: int = 0
    anzahl_rauchmelder: int = 0
    anzahl_sprinkler: int = 0
    gesamtflaeche_ex_m2: float = 0.0
    
    # Prüfergebnisse
    warnungen: list[str] = field(default_factory=list)
    maengel: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "fluchtwege": [f.to_dict() for f in self.fluchtwege],
            "brandabschnitte": [b.to_dict() for b in self.brandabschnitte],
            "ex_bereiche": [e.to_dict() for e in self.ex_bereiche],
            "einrichtungen": [e.to_dict() for e in self.einrichtungen],
            "zusammenfassung": {
                "notausgaenge": self.anzahl_notausgaenge,
                "feuerloescher": self.anzahl_feuerloescher,
                "rauchmelder": self.anzahl_rauchmelder,
                "sprinkler": self.anzahl_sprinkler,
                "ex_flaeche_m2": self.gesamtflaeche_ex_m2,
            },
            "warnungen": self.warnungen,
            "maengel": self.maengel,
        }



# ============================================================
# Symbol Models
# ============================================================


class SymbolTyp(Enum):
    """Brandschutz-Symboltypen nach DIN EN ISO 7010."""
    # Rettungszeichen (grün)
    NOTAUSGANG = "E001"           # Notausgang
    NOTAUSGANG_LINKS = "E001-L"   # Notausgang links
    NOTAUSGANG_RECHTS = "E001-R"  # Notausgang rechts
    SAMMELSTELLE = "E007"         # Sammelstelle
    ERSTE_HILFE = "E003"          # Erste Hilfe
    
    # Brandschutzzeichen (rot)
    FEUERLOESCHER = "F001"        # Feuerlöscher
    LOESCHDECKE = "F002"          # Löschdecke
    FEUERLEITER = "F003"          # Feuerleiter
    BRANDMELDER = "F005"          # Brandmelder
    WANDHYDRANT = "F002"          # Löschschlauch
    
    # Warnzeichen (gelb)
    WARNUNG_FEUER = "W021"        # Feuergefährliche Stoffe
    WARNUNG_EX = "W021"           # Explosionsgefahr
    
    # Sonstige
    RAUCHMELDER = "RM"            # Rauchmelder (kein ISO)
    SPRINKLER = "SP"              # Sprinkler
    RWA = "RWA"                   # Rauch-Wärme-Abzug
    FLUCHTWEG_PFEIL = "FW"        # Fluchtweg-Richtungspfeil


@dataclass
class PlatzierungsRegel:
    """Regel für Symbol-Platzierung."""
    symbol_typ: SymbolTyp
    max_abstand_m: float = 0.0      # Max Abstand zwischen Symbolen
    max_flaeche_m2: float = 0.0     # Max Fläche pro Symbol
    min_anzahl: int = 0              # Mindestanzahl
    an_tueren: bool = False          # An Türen platzieren
    an_fluchtwegen: bool = False     # Entlang Fluchtwegen
    an_richtungswechsel: bool = False  # Bei Richtungswechseln
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
    prioritaet: int = 1  # 1=kritisch, 2=empfohlen, 3=optional
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SymbolInsertionResult:
    """Ergebnis der Symbol-Analyse und -Einfügung."""
    vorgeschlagene_symbole: list[SymbolPlatzierung] = field(default_factory=list)
    eingefuegte_symbole: list[SymbolPlatzierung] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    
    # Statistik
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
            }
        }



# ============================================================
# Report Models
# ============================================================


class BerichtKonfiguration:
    """Konfiguration für Berichtserstellung."""
    titel: str = "Brandschutz-Prüfbericht"
    projekt_name: str = ""
    etage: str = ""
    pruefer: str = ""
    datum: str = ""
    
    # Inhalte
    mit_zusammenfassung: bool = True
    mit_maengelliste: bool = True
    mit_symboluebersicht: bool = True
    mit_fluchtweganalyse: bool = True
    mit_regelwerkreferenzen: bool = True
    mit_empfehlungen: bool = True
    mit_grafiken: bool = True
    
    # Ausgabeformat
    format: str = "pdf"  # pdf, excel, json, html

