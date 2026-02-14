"""
IFC Export Views

Export views for Raumbuch, WoFlV, GAEB, X83 formats.
"""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View

from .models import Door, Floor, IFCModel, Room, Slab, Wall, Window


class ExportRaumbuchView(View):
    """Raumbuch als Excel exportieren"""

    def get(self, request, model_id):
        ifc_model = get_object_or_404(IFCModel, pk=model_id)
        export_type = request.GET.get("type", "raumbuch")

        from apps.export.services.export_service import RaumbuchExportService

        service = RaumbuchExportService()

        if export_type == "din277":
            output = service.export_din277_summary(ifc_model)
            filename = f"DIN277_{ifc_model.project.name}_v{ifc_model.version}.xlsx"
        else:
            output = service.export_to_excel(ifc_model)
            filename = f"Raumbuch_{ifc_model.project.name}_v{ifc_model.version}.xlsx"

        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


class ExportWoFlVView(View):
    """WoFlV Wohnflächenberechnung als Excel exportieren"""

    def get(self, request, model_id):
        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        ifc_model = get_object_or_404(IFCModel, pk=model_id)

        # WoFlV berechnen
        from .services import WoFlVCalculator

        rooms = list(
            Room.objects.filter(ifc_model=ifc_model).values("name", "number", "area", "height")
        )

        calculator = WoFlVCalculator()
        result = calculator.calculate_from_rooms(rooms)

        # Excel erstellen
        wb = Workbook()
        ws = wb.active
        ws.title = "WoFlV Berechnung"

        # Header
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")

        ws["A1"] = f"WoFlV Wohnflächenberechnung"
        ws["A1"].font = Font(bold=True, size=14)
        ws["A2"] = ifc_model.project.name

        # Zusammenfassung
        ws["A4"] = "Zusammenfassung"
        ws["A4"].font = Font(bold=True, size=12)

        summary_data = [
            ("Grundfläche gesamt:", float(result.grundflaeche_gesamt), "m²"),
            ("Wohnfläche 100%:", float(result.wohnflaeche_100), "m²"),
            ("Wohnfläche 50%:", float(result.wohnflaeche_50), "m²"),
            ("Wohnfläche 25%:", float(result.wohnflaeche_25), "m²"),
            ("Nicht angerechnet:", float(result.nicht_angerechnet), "m²"),
            ("", "", ""),
            ("WOHNFLÄCHE GESAMT:", float(result.wohnflaeche_gesamt), "m²"),
            ("Anrechnungsquote:", result.anrechnungsquote * 100, "%"),
        ]

        for idx, (label, value, unit) in enumerate(summary_data, 5):
            ws.cell(row=idx, column=1, value=label)
            if value:
                ws.cell(row=idx, column=2, value=value).number_format = "#,##0.00"
            ws.cell(row=idx, column=3, value=unit)

        # Raumdetails
        ws["A15"] = "Raumdetails"
        ws["A15"].font = Font(bold=True, size=12)

        headers = ["Nr.", "Raumname", "Grundfläche", "Höhe", "Typ", "Faktor", "Wohnfläche"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=16, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill

        for row_idx, room in enumerate(result.rooms, 17):
            ws.cell(row=row_idx, column=1, value=room.number)
            ws.cell(row=row_idx, column=2, value=room.name)
            ws.cell(row=row_idx, column=3, value=float(room.grundflaeche)).number_format = (
                "#,##0.00"
            )
            ws.cell(row=row_idx, column=4, value=float(room.hoehe)).number_format = "0.00"
            ws.cell(row=row_idx, column=5, value=room.raumtyp)
            ws.cell(row=row_idx, column=6, value=float(room.gesamt_faktor)).number_format = "0%"
            ws.cell(row=row_idx, column=7, value=float(room.wohnflaeche)).number_format = "#,##0.00"

        # Spaltenbreiten
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 25

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"WoFlV_{ifc_model.project.name}_v{ifc_model.version}.xlsx"
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ExportGAEBView(View):
    """GAEB Leistungsverzeichnis exportieren"""

    def get(self, request, model_id):
        from decimal import Decimal

        ifc_model = get_object_or_404(IFCModel, pk=model_id)
        format_type = request.GET.get("format", "excel")  # excel oder xml

        from .services import (
            GAEBGenerator,
            Leistungsverzeichnis,
            LosGruppe,
            MassenermittlungHelper,
            MengenEinheit,
            Position,
        )

        # Räume laden
        rooms = list(
            Room.objects.filter(ifc_model=ifc_model).values("name", "number", "area", "perimeter")
        )

        # LV erstellen mit Massenermittlung
        lv = Leistungsverzeichnis(
            projekt_name=ifc_model.project.name,
            projekt_nummer=str(ifc_model.project.pk)[:8],
        )

        # Los 1: Bodenbeläge
        boden_positionen = MassenermittlungHelper.from_rooms(
            rooms, gewerk="Bodenbelag", oz_prefix="01"
        )
        lv.lose.append(LosGruppe(oz="01", bezeichnung="Bodenbeläge", positionen=boden_positionen))

        # Los 2: Sockelleisten
        sockel_positionen = MassenermittlungHelper.from_room_perimeters(
            rooms, gewerk="Sockelleisten", oz_prefix="02"
        )
        if sockel_positionen:
            lv.lose.append(
                LosGruppe(oz="02", bezeichnung="Sockelleisten", positionen=sockel_positionen)
            )

        # Export
        generator = GAEBGenerator()

        if format_type == "xml":
            output = generator.generate_xml(lv)
            content_type = "application/xml"
            filename = f"LV_{ifc_model.project.name}_v{ifc_model.version}.x84"
        else:
            output = generator.generate_excel(lv)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"LV_{ifc_model.project.name}_v{ifc_model.version}.xlsx"

        response = HttpResponse(output.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ExportX83View(View):
    """
    IFC → GAEB X83 Export (Angebot mit Mengen und Preisen)
    
    Extrahiert alle Mengen aus dem IFC-Modell und erstellt
    ein vollständiges Leistungsverzeichnis nach GAEB X83.
    
    Query-Parameter:
        format: xml (default) oder excel
        gewerke: kommaseparierte Liste (z.B. bodenbelag,tueren,fenster)
        prices: 1/0 - Einheitspreise inkludieren
    """

    def get(self, request, model_id):
        ifc_model = get_object_or_404(IFCModel, pk=model_id)
        
        format_type = request.GET.get("format", "xml")
        include_prices = request.GET.get("prices", "1") == "1"
        gewerke_param = request.GET.get("gewerke", "")
        
        selected_gewerke = None
        if gewerke_param:
            selected_gewerke = [g.strip() for g in gewerke_param.split(",")]
        
        from .services import get_ifc_x83_converter
        
        # IFC-Daten aus Datenbank laden
        ifc_data = self._extract_ifc_data(ifc_model)
        
        # Konvertieren
        converter = get_ifc_x83_converter()
        
        if format_type == "excel":
            output = converter.convert_to_excel(
                ifc_data=ifc_data,
                projekt_name=ifc_model.project.name,
                projekt_nummer=str(ifc_model.project.pk)[:8],
                include_prices=include_prices,
                selected_gewerke=selected_gewerke,
            )
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"LV_X83_{ifc_model.project.name}_v{ifc_model.version}.xlsx"
        else:
            output = converter.convert_to_x83(
                ifc_data=ifc_data,
                projekt_name=ifc_model.project.name,
                projekt_nummer=str(ifc_model.project.pk)[:8],
                include_prices=include_prices,
                selected_gewerke=selected_gewerke,
            )
            content_type = "application/xml"
            filename = f"LV_{ifc_model.project.name}_v{ifc_model.version}.x83"
        
        response = HttpResponse(output.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    
    def _extract_ifc_data(self, ifc_model) -> dict:
        """Extrahiert IFC-Daten aus der Datenbank."""
        rooms = list(
            Room.objects.filter(ifc_model=ifc_model).values(
                "name", "number", "area", "perimeter", "height", "volume"
            )
        )
        
        walls = list(
            Wall.objects.filter(ifc_model=ifc_model).values(
                "name", "ifc_guid", "length", "height", "thickness"
            )
        )
        # Wandfläche berechnen
        for wall in walls:
            wall["area"] = (wall.get("length", 0) or 0) * (wall.get("height", 0) or 0)
        
        doors = list(
            Door.objects.filter(ifc_model=ifc_model).values(
                "name", "ifc_guid", "width", "height"
            )
        )
        # Türtyp aus Name extrahieren
        for door in doors:
            door["type"] = "Standard"
            if "brand" in (door.get("name", "") or "").lower():
                door["type"] = "Brandschutz"
        
        windows = list(
            Window.objects.filter(ifc_model=ifc_model).values(
                "name", "ifc_guid", "width", "height"
            )
        )
        
        slabs = list(
            Slab.objects.filter(ifc_model=ifc_model).values(
                "name", "ifc_guid", "area", "thickness"
            )
        )
        
        return {
            "rooms": rooms,
            "walls": walls,
            "doors": doors,
            "windows": windows,
            "slabs": slabs,
        }


