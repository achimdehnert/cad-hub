# apps/cad_hub/views_brandschutz.py
"""
Views für Brandschutz-Frontend.
"""

import json
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .handlers import BrandschutzHandler, BrandschutzReportHandler, BrandschutzSymbolHandler
from .models import (
    BrandschutzMangel,
    BrandschutzPruefung,
    PruefStatus,
)
from .services import brandschutz_service


class BrandschutzDashboardView(LoginRequiredMixin, View):
    """Brandschutz Dashboard - Übersicht aller Prüfungen."""

    template_name = "cad_hub/brandschutz/dashboard.html"

    def get(self, request):
        context = {
            "stats": brandschutz_service.get_dashboard_stats(),
            "mangel_stats": brandschutz_service.get_mangel_stats(),
            "letzte_pruefungen": brandschutz_service.get_letzte_pruefungen(),
            "dringende_maengel": brandschutz_service.get_dringende_maengel(),
            "page_title": "Brandschutz Dashboard",
        }
        return render(request, self.template_name, context)


class BrandschutzPruefungListView(LoginRequiredMixin, ListView):
    """Liste aller Brandschutz-Prüfungen."""

    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_list.html"
    context_object_name = "pruefungen"
    paginate_by = 20

    def get_queryset(self):
        return brandschutz_service.get_pruefung_list_queryset(
            status=self.request.GET.get("status"),
            search=self.request.GET.get("q"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = PruefStatus.choices
        context["current_status"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["page_title"] = "Brandschutz-Prüfungen"
        return context


class BrandschutzPruefungDetailView(LoginRequiredMixin, DetailView):
    """Detail-Ansicht einer Prüfung."""

    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_detail.html"
    context_object_name = "pruefung"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pruefung = self.object

        # Mängel gruppiert nach Kategorie
        maengel = pruefung.maengel.all().order_by("schweregrad", "-erstellt_am")
        maengel_by_kategorie = {}
        for mangel in maengel:
            kat = mangel.kategorie
            if kat not in maengel_by_kategorie:
                maengel_by_kategorie[kat] = []
            maengel_by_kategorie[kat].append(mangel)

        # Symbole gruppiert nach Typ
        symbole = pruefung.symbole.all().order_by("prioritaet")
        symbole_by_typ = {}
        for symbol in symbole:
            typ = symbol.symbol_typ
            if typ not in symbole_by_typ:
                symbole_by_typ[typ] = []
            symbole_by_typ[typ].append(symbol)

        context["maengel"] = maengel
        context["maengel_by_kategorie"] = maengel_by_kategorie
        context["symbole"] = symbole
        context["symbole_by_typ"] = symbole_by_typ
        context["page_title"] = f"Prüfung: {pruefung.titel}"
        return context


class BrandschutzPruefungCreateView(LoginRequiredMixin, CreateView):
    """Neue Prüfung erstellen."""

    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_form.html"
    fields = [
        "titel",
        "projekt_name",
        "gebaeude_typ",
        "etage",
        "flaeche_qm",
        "beschreibung",
        "pruefer",
        "quelldatei",
    ]
    success_url = reverse_lazy("brandschutz:pruefung_list")

    def form_valid(self, form):
        form.instance.status = PruefStatus.ENTWURF
        messages.success(self.request, "Prüfung erfolgreich erstellt.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Neue Brandschutz-Prüfung"
        context["form_action"] = "Erstellen"
        return context


class BrandschutzPruefungUpdateView(LoginRequiredMixin, UpdateView):
    """Prüfung bearbeiten."""

    model = BrandschutzPruefung
    template_name = "cad_hub/brandschutz/pruefung_form.html"
    fields = [
        "titel",
        "projekt_name",
        "status",
        "gebaeude_typ",
        "etage",
        "flaeche_qm",
        "beschreibung",
        "pruefer",
        "naechste_pruefung",
    ]

    def get_success_url(self):
        return reverse("brandschutz:pruefung_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Prüfung erfolgreich aktualisiert.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Bearbeiten: {self.object.titel}"
        context["form_action"] = "Speichern"
        return context


class BrandschutzAnalyseView(LoginRequiredMixin, View):
    """Analyse einer CAD-Datei durchführen."""

    template_name = "cad_hub/brandschutz/analyse.html"

    def get(self, request, pk=None):
        pruefung = None
        if pk:
            pruefung = get_object_or_404(BrandschutzPruefung, pk=pk)

        context = {
            "pruefung": pruefung,
            "page_title": "Brandschutz-Analyse",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None):
        """HTMX: Analyse durchführen."""
        pruefung = get_object_or_404(BrandschutzPruefung, pk=pk) if pk else None

        # Datei aus Request oder Prüfung
        uploaded_file = request.FILES.get("datei")
        if not uploaded_file and pruefung and pruefung.quelldatei:
            file_path = pruefung.quelldatei.path
        elif uploaded_file:
            # Temporär speichern
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                file_path = tmp.name
        else:
            return JsonResponse({"error": "Keine Datei angegeben"}, status=400)

        try:
            # Handler initialisieren
            bs_handler = BrandschutzHandler()
            sym_handler = BrandschutzSymbolHandler()

            # Format erkennen
            suffix = Path(file_path).suffix.lower()
            if suffix == ".dxf":
                import ezdxf

                doc = ezdxf.readfile(file_path)
                analyse_input = {"loader": doc, "format": "dxf"}
            elif suffix == ".ifc":
                import ifcopenshell

                model = ifcopenshell.open(file_path)
                analyse_input = {"loader": model, "format": "ifc"}
            else:
                return JsonResponse({"error": f"Unbekanntes Format: {suffix}"}, status=400)

            # Analyse durchführen
            result = bs_handler.execute(analyse_input)

            if result.success:
                # Symbol-Vorschläge generieren
                sym_result = sym_handler.execute(
                    {
                        "analyse_ergebnis": result.data,
                        "format": suffix.strip("."),
                    }
                )

                # Prüfung aktualisieren
                if pruefung:
                    brandschutz_service.update_pruefung_after_analyse(pruefung, result.data)
                    brandschutz_service.create_maengel_from_analyse(pruefung, result.data)

                    if sym_result.success:
                        brandschutz_service.create_symbole_from_analyse(
                            pruefung, sym_result.data
                        )

                return JsonResponse(
                    {
                        "success": True,
                        "analyse": result.data,
                        "symbole": sym_result.data if sym_result.success else {},
                        "redirect": reverse(
                            "brandschutz:pruefung_detail", kwargs={"pk": pruefung.pk}
                        )
                        if pruefung
                        else None,
                    }
                )
            else:
                return JsonResponse({"error": str(result.errors)}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class BrandschutzReportView(LoginRequiredMixin, View):
    """Report generieren."""

    def get(self, request, pk, format="html"):
        pruefung = get_object_or_404(BrandschutzPruefung, pk=pk)

        # Report-Handler
        handler = BrandschutzReportHandler()

        # Daten sammeln
        maengel = list(
            pruefung.maengel.values(
                "kategorie", "schweregrad", "beschreibung", "regelwerk_referenz", "behoben"
            )
        )
        symbole = list(
            pruefung.symbole.values(
                "symbol_typ", "position_x", "position_y", "status", "begruendung"
            )
        )

        result = handler.execute(
            {
                "analyse_ergebnis": pruefung.analyse_ergebnis or {},
                "symbol_ergebnis": {"symbole": {"vorgeschlagene_symbole": symbole}},
                "format": format,
                "konfiguration": {
                    "projekt_name": pruefung.projekt_name,
                    "etage": pruefung.etage or "-",
                    "pruefer": pruefung.pruefer or "-",
                    "pruef_datum": pruefung.pruef_datum.isoformat()
                    if pruefung.pruef_datum
                    else "-",
                    "maengel_liste": maengel,
                },
            }
        )

        if not result.success:
            messages.error(request, f"Report-Fehler: {result.errors}")
            return redirect("brandschutz:pruefung_detail", pk=pk)

        # Response je nach Format
        if format == "html":
            return HttpResponse(result.data["bericht"], content_type="text/html")
        elif format == "pdf":
            response = HttpResponse(result.data["bericht"], content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="brandschutz_report_{pk}.pdf"'
            return response
        elif format == "excel":
            response = HttpResponse(
                result.data["bericht"],
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="brandschutz_report_{pk}.xlsx"'
            return response
        elif format == "json":
            return JsonResponse(json.loads(result.data["bericht"].decode()))

        return HttpResponse(result.data["bericht"])


class BrandschutzMangelToggleView(LoginRequiredMixin, View):
    """HTMX: Mangel als behoben markieren."""

    def post(self, request, pk):
        mangel = get_object_or_404(BrandschutzMangel, pk=pk)
        mangel = brandschutz_service.toggle_mangel(mangel)

        # HTMX partial response
        return render(request, "cad_hub/brandschutz/partials/mangel_row.html", {"mangel": mangel})


class BrandschutzSymbolApproveView(LoginRequiredMixin, View):
    """HTMX: Symbol genehmigen/ablehnen."""

    def post(self, request, pk):
        symbol = get_object_or_404(BrandschutzSymbol, pk=pk)
        action = request.POST.get("action", "genehmigt")

        if action in ["genehmigt", "abgelehnt", "eingefuegt"]:
            symbol.status = action
            symbol.save()

        return render(request, "cad_hub/brandschutz/partials/symbol_row.html", {"symbol": symbol})


class BrandschutzRegelwerkListView(LoginRequiredMixin, ListView):
    """Liste aller Regelwerke."""

    model = BrandschutzRegelwerk
    template_name = "cad_hub/brandschutz/regelwerk_list.html"
    context_object_name = "regelwerke"

    def get_queryset(self):
        return super().get_queryset().filter(aktiv=True).order_by("kuerzel")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Brandschutz-Regelwerke"
        return context


# API Endpoints für HTMX


class BrandschutzStatsAPIView(LoginRequiredMixin, View):
    """API: Dashboard-Statistiken."""

    def get(self, request):
        return JsonResponse(brandschutz_service.get_api_stats())


class BrandschutzSearchAPIView(LoginRequiredMixin, View):
    """API: Suche in Prüfungen."""

    def get(self, request):
        query = request.GET.get("q", "")

        if len(query) < 2:
            return JsonResponse({"results": []})

        results = brandschutz_service.search_pruefungen(query)
        for r in results:
            r["url"] = reverse("brandschutz:pruefung_detail", kwargs={"pk": r.pop("pk")})

        return JsonResponse({"results": results})
