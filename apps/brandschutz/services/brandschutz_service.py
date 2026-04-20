"""
Brandschutz Service Layer (ADR-041).

Encapsulates all ORM queries for the Brandschutz module.
Views must not access Model.objects directly.
"""

from datetime import datetime

from django.db.models import Count, Q

from ..models import (
    BrandschutzKategorie,
    BrandschutzMangel,
    BrandschutzPruefung,
    BrandschutzRegelwerk,
    BrandschutzSymbolVorschlag,
    PruefStatus,
)


def get_dashboard_stats() -> dict:
    """Aggregated statistics for the Brandschutz dashboard."""
    pruefungen = BrandschutzPruefung.objects.all()
    return {
        "gesamt": pruefungen.count(),
        "entwurf": pruefungen.filter(status=PruefStatus.ENTWURF).count(),
        "in_pruefung": pruefungen.filter(status=PruefStatus.IN_PRUEFUNG).count(),
        "abgeschlossen": pruefungen.filter(status=PruefStatus.ABGESCHLOSSEN).count(),
        "maengel": pruefungen.filter(status=PruefStatus.MAENGEL).count(),
        "freigegeben": pruefungen.filter(status=PruefStatus.FREIGEGEBEN).count(),
    }


def get_mangel_stats() -> dict:
    """Open defect statistics."""
    offene = BrandschutzMangel.objects.filter(behoben=False)
    return {
        "gesamt": offene.count(),
        "kritisch": offene.filter(schweregrad="kritisch").count(),
        "hoch": offene.filter(schweregrad="hoch").count(),
        "mittel": offene.filter(schweregrad="mittel").count(),
        "gering": offene.filter(schweregrad="gering").count(),
    }


def get_letzte_pruefungen(limit: int = 5):
    """Most recent inspections."""
    return BrandschutzPruefung.objects.order_by("-pruef_datum")[:limit]


def get_dringende_maengel(limit: int = 10):
    """Critical and high severity open defects."""
    return (
        BrandschutzMangel.objects.filter(behoben=False, schweregrad__in=["kritisch", "hoch"])
        .select_related("pruefung")
        .order_by("-erstellt_am")[:limit]
    )


def get_offene_maengel_for_dashboard():
    """Open defects with related pruefung (for dashboard context)."""
    return BrandschutzMangel.objects.filter(behoben=False).select_related("pruefung")


def get_pruefung_list_queryset(status: str | None = None, search: str | None = None):
    """Filtered and annotated Pruefung queryset for list view."""
    queryset = BrandschutzPruefung.objects.annotate(
        mangel_count=Count("maengel"),
        offene_maengel=Count("maengel", filter=Q(maengel__behoben=False)),
    ).order_by("-pruef_datum")

    if status:
        queryset = queryset.filter(status=status)

    if search:
        queryset = queryset.filter(
            Q(titel__icontains=search)
            | Q(projekt_name__icontains=search)
            | Q(pruefer__icontains=search)
        )

    return queryset


def create_maengel_from_analyse(pruefung: BrandschutzPruefung, analyse_data: dict) -> list:
    """Create BrandschutzMangel records from analysis result."""
    created = []
    for mangel_text in analyse_data.get("brandschutz", {}).get("maengel", []):
        mangel = BrandschutzMangel.objects.create(
            pruefung=pruefung,
            kategorie=BrandschutzKategorie.FLUCHTWEG,
            schweregrad="hoch",
            beschreibung=mangel_text,
        )
        created.append(mangel)
    return created


def create_symbole_from_analyse(pruefung: BrandschutzPruefung, sym_data: dict) -> list:
    """Create BrandschutzSymbolVorschlag records from symbol analysis."""
    created = []
    for sym in sym_data.get("symbole", {}).get("vorgeschlagene_symbole", []):
        symbol = BrandschutzSymbolVorschlag.objects.create(
            pruefung=pruefung,
            symbol_typ=sym.get("symbol_typ", "UNBEKANNT"),
            position_x=sym.get("position_x", 0),
            position_y=sym.get("position_y", 0),
            begruendung=sym.get("begruendung", ""),
            prioritaet=sym.get("prioritaet", 3),
            status="vorgeschlagen",
        )
        created.append(symbol)
    return created


def update_pruefung_after_analyse(pruefung: BrandschutzPruefung, analyse_data: dict) -> None:
    """Update inspection status after analysis."""
    pruefung.analyse_ergebnis = analyse_data
    pruefung.status = PruefStatus.IN_PRUEFUNG
    pruefung.save()


def toggle_mangel(mangel: BrandschutzMangel) -> BrandschutzMangel:
    """Toggle defect resolved status."""
    mangel.behoben = not mangel.behoben
    mangel.behoben_am = datetime.now() if mangel.behoben else None
    mangel.save()
    return mangel


def get_api_stats() -> dict:
    """Dashboard API statistics."""
    pruefungen = BrandschutzPruefung.objects.all()
    maengel = BrandschutzMangel.objects.filter(behoben=False)
    return {
        "pruefungen": {
            "gesamt": pruefungen.count(),
            "offen": pruefungen.exclude(status=PruefStatus.FREIGEGEBEN).count(),
        },
        "maengel": {
            "offen": maengel.count(),
            "kritisch": maengel.filter(schweregrad="kritisch").count(),
        },
    }


def search_pruefungen(query: str, limit: int = 10) -> list[dict]:
    """Search inspections by title or project name."""
    pruefungen = BrandschutzPruefung.objects.filter(
        Q(titel__icontains=query) | Q(projekt_name__icontains=query)
    )[:limit]

    return [
        {
            "id": str(p.pk),
            "titel": p.titel,
            "projekt": p.projekt_name,
            "status": p.get_status_display(),
            "pk": p.pk,
        }
        for p in pruefungen
    ]


def get_active_regelwerke():
    """Active regulation frameworks, ordered by abbreviation."""
    return BrandschutzRegelwerk.objects.filter(aktiv=True).order_by("kuerzel")
