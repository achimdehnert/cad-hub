# apps/cad_hub/views.py
"""
Views für IFC Dashboard
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.core.mixins import TenantMixin

from .models import Floor, IFCModel, IFCProject, Room


class HtmxMixin:
    """Mixin für HTMX-Support: Liefert Partial bei HTMX-Request"""

    partial_template_name = None

    def get_template_names(self):
        if self.request.headers.get("HX-Request") and self.partial_template_name:
            return [self.partial_template_name]
        return super().get_template_names()


# =============================================================================
# Dashboard
# =============================================================================


class DashboardView(TenantMixin, TemplateView):
    """Haupt-Dashboard mit Übersicht"""

    template_name = "cad_hub/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tid = self._tenant_id()

        ctx["recent_projects"] = (
            IFCProject.objects.filter(tenant_id=tid)[:5] if tid else IFCProject.objects.none()
        )
        ctx["stats"] = {
            "projects": IFCProject.objects.filter(tenant_id=tid).count() if tid else 0,
            "models": IFCModel.objects.filter(tenant_id=tid, status="ready").count() if tid else 0,
            "rooms": Room.objects.filter(tenant_id=tid).count() if tid else 0,
        }

        return ctx


# =============================================================================
# Projekte
# =============================================================================


class ProjectListView(TenantMixin, HtmxMixin, ListView):
    """Liste aller Projekte"""

    model = IFCProject
    template_name = "cad_hub/project_list.html"
    partial_template_name = "cad_hub/partials/_project_list.html"
    context_object_name = "projects"
    paginate_by = 10


class ProjectDetailView(TenantMixin, DetailView):
    """Projekt-Detail mit Modellversionen"""

    model = IFCProject
    template_name = "cad_hub/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["models"] = self.object.models.all()
        return ctx


class ProjectCreateView(TenantMixin, LoginRequiredMixin, CreateView):
    """Neues Projekt erstellen"""

    model = IFCProject
    template_name = "cad_hub/project_form.html"
    fields = ["name"]
    success_url = reverse_lazy("ifc:project_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(TenantMixin, LoginRequiredMixin, UpdateView):
    """Projekt-Name bearbeiten"""

    model = IFCProject
    template_name = "cad_hub/project_form.html"
    fields = ["name"]

    def get_success_url(self):
        return reverse_lazy("ifc:project_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Projekt "{form.instance.name}" erfolgreich aktualisiert.')
        return super().form_valid(form)


class ProjectDeleteView(TenantMixin, LoginRequiredMixin, DeleteView):
    """Projekt löschen (inkl. aller Modelle)"""

    model = IFCProject
    template_name = "cad_hub/project_confirm_delete.html"
    success_url = reverse_lazy("ifc:project_list")

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        messages.success(
            request, f'Projekt "{project.name}" und alle zugehörigen IFC-Versionen wurden gelöscht.'
        )
        return super().delete(request, *args, **kwargs)


# =============================================================================
# Modelle
# =============================================================================


class ModelDetailView(TenantMixin, DetailView):
    """IFC-Modell Detail"""

    model = IFCModel
    template_name = "cad_hub/model_detail.html"
    context_object_name = "model"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = self.get_object()

        # Geschosse mit Raumanzahl
        floors = model.floors.annotate(room_count=Count("rooms")).order_by("sort_order")

        ctx["floors"] = floors
        ctx["room_count"] = model.rooms.count()
        return ctx


class ModelViewerView(TenantMixin, DetailView):
    """3D Viewer für IFC-Modell"""

    model = IFCModel
    template_name = "cad_hub/model_viewer.html"
    context_object_name = "model"


class IFCContentOverviewView(TenantMixin, DetailView):
    """IFC Inhalts-Übersicht: Alle extrahierten Elemente in Tabellen"""

    model = IFCModel
    template_name = "cad_hub/ifc_content_overview.html"
    context_object_name = "model"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = self.object

        # Aggregierte Statistiken
        ctx["stats"] = {
            "floors": model.floors.count(),
            "rooms": model.rooms.count(),
            "windows": model.windows.count(),
            "doors": model.doors.count(),
            "walls": model.walls.count(),
            "slabs": model.slabs.count(),
            # Flächen
            "total_room_area": model.rooms.aggregate(Sum("area"))["area__sum"] or 0,
            "total_wall_gross_area": model.walls.aggregate(Sum("gross_area"))["gross_area__sum"]
            or 0,
            "total_wall_net_area": model.walls.aggregate(Sum("net_area"))["net_area__sum"] or 0,
            "total_slab_area": model.slabs.aggregate(Sum("area"))["area__sum"] or 0,
            # Wände
            "external_walls": model.walls.filter(is_external=True).count(),
            "internal_walls": model.walls.filter(is_external=False).count(),
        }

        # Pro Geschoss
        ctx["floors_with_stats"] = []
        for floor in model.floors.all():
            ctx["floors_with_stats"].append(
                {
                    "floor": floor,
                    "rooms": floor.rooms.count(),
                    "windows": floor.windows.count(),
                    "doors": floor.doors.count(),
                    "walls": floor.walls.count(),
                    "slabs": floor.slabs.count(),
                    "room_area": floor.rooms.aggregate(Sum("area"))["area__sum"] or 0,
                }
            )

        # Beispieldaten (erste 5 pro Typ)
        ctx["sample_rooms"] = model.rooms.all()[:5]
        ctx["sample_windows"] = model.windows.all()[:5]
        ctx["sample_doors"] = model.doors.all()[:5]
        ctx["sample_walls"] = model.walls.all()[:5]
        ctx["sample_slabs"] = model.slabs.all()[:5]

        return ctx


class ModelUploadView(TenantMixin, LoginRequiredMixin, CreateView):
    """IFC-Datei hochladen"""

    model = IFCModel
    template_name = "cad_hub/model_upload.html"
    fields = ["ifc_file"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tid = self._tenant_id()
        ctx["project"] = get_object_or_404(IFCProject, pk=self.kwargs["project_id"], tenant_id=tid)
        return ctx

    def form_valid(self, form):
        tid = self._tenant_id()
        project = get_object_or_404(IFCProject, pk=self.kwargs["project_id"], tenant_id=tid)

        last = IFCModel.objects.filter(project=project).order_by("-version").first()

        form.instance.tenant_id = tid
        form.instance.project = project
        form.instance.version = (last.version + 1) if last else 1
        form.instance.status = IFCModel.Status.UPLOADING

        response = super().form_valid(form)

        from .tasks import process_ifc_upload

        process_ifc_upload.delay(str(self.object.pk))

        return response

    def get_success_url(self):
        return reverse_lazy("ifc:model_detail", kwargs={"pk": self.object.pk})


class CADUploadView(LoginRequiredMixin, TemplateView):
    """DWG/DXF/PDF/GAEB Upload mit Multi-Format Support"""

    template_name = "cad_hub/cad_upload.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = get_object_or_404(IFCProject, pk=self.kwargs["project_id"])
        ctx["supported_formats"] = {
            "dwg": {"name": "AutoCAD DWG", "icon": "📐", "description": "AutoCAD Zeichnung"},
            "dxf": {"name": "AutoCAD DXF", "icon": "📐", "description": "Drawing Exchange Format"},
            "pdf": {"name": "PDF Plan", "icon": "📄", "description": "Gescannte Baupläne"},
            "x83": {
                "name": "GAEB X83",
                "icon": "📋",
                "description": "Leistungsverzeichnis (Angebot)",
            },
        }
        return ctx

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(IFCProject, pk=self.kwargs["project_id"])
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Keine Datei ausgewählt.")
            return redirect("ifc:cad_upload", project_id=project.pk)

        # Dateiendung prüfen
        file_ext = uploaded_file.name.split(".")[-1].lower()

        if file_ext not in ["dwg", "dxf", "pdf", "x83", "x84"]:
            messages.error(request, f"Format .{file_ext} wird nicht unterstützt.")
            return redirect("ifc:cad_upload", project_id=project.pk)

        # Placeholder: In Zukunft MCP Backend Integration
        messages.info(
            request,
            f"Upload erfolgreich! Format: {file_ext.upper()} - "
            f"Konvertierung zu IFC folgt in zukünftiger Version.",
        )

        return redirect("ifc:project_detail", pk=project.pk)


class ModelDeleteView(LoginRequiredMixin, DeleteView):
    """IFC-Version löschen"""

    model = IFCModel
    template_name = "cad_hub/model_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("ifc:project_detail", kwargs={"pk": self.object.project.pk})

    def delete(self, request, *args, **kwargs):
        model = self.get_object()
        messages.success(request, f"IFC-Version {model.version} wurde gelöscht.")
        return super().delete(request, *args, **kwargs)


# =============================================================================
# Räume
# =============================================================================


class RoomListView(HtmxMixin, ListView):
    """Raumliste mit Filterung"""

    model = Room
    template_name = "cad_hub/room_list.html"
    partial_template_name = "cad_hub/partials/_room_table.html"
    context_object_name = "rooms"
    paginate_by = 20

    def get_queryset(self):
        model_id = self.kwargs["model_id"]
        qs = Room.objects.filter(ifc_model_id=model_id)

        # Filter: Geschoss
        if floor := self.request.GET.get("floor"):
            qs = qs.filter(floor_id=floor)

        # Filter: Nutzung
        if usage := self.request.GET.get("usage"):
            qs = qs.filter(usage_category=usage)

        # Suche
        if search := self.request.GET.get("q"):
            qs = qs.filter(name__icontains=search)

        return qs.select_related("floor").order_by("number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model_id = self.kwargs["model_id"]

        ctx["ifc_model"] = get_object_or_404(IFCModel, pk=model_id)
        ctx["floors"] = Floor.objects.filter(ifc_model_id=model_id)
        ctx["usage_choices"] = Room.UsageCategory.choices

        return ctx


class RoomDetailView(HtmxMixin, DetailView):
    """Raum-Detail (für Seitenpanel)"""

    model = Room
    template_name = "cad_hub/room_detail.html"
    partial_template_name = "cad_hub/partials/_room_detail.html"
    context_object_name = "room"


# =============================================================================
# Flächen
# =============================================================================


class AreaSummaryView(HtmxMixin, TemplateView):
    """DIN 277 Flächenübersicht"""

    template_name = "cad_hub/area_summary.html"
    partial_template_name = "cad_hub/partials/_area_summary.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model_id = self.kwargs["model_id"]

        # Get model and project reference
        ifc_model = get_object_or_404(IFCModel, pk=model_id)

        # Einfache Flächenberechnung aus Räumen
        rooms = Room.objects.filter(ifc_model=ifc_model)
        total_area = rooms.aggregate(Sum("area"))["area__sum"] or 0

        ctx["areas"] = {
            "bgf": total_area,
            "ngf": total_area * 0.85,  # Beispiel: 85% als Nutzfläche
            "nf": total_area * 0.75,
            "tf": total_area * 0.10,
            "vf": total_area * 0.05,
        }
        ctx["din277"] = {
            "total_area": total_area,
            "rooms_count": rooms.count(),
        }
        ctx["ifc_model"] = ifc_model

        return ctx


class WoFlVSummaryView(HtmxMixin, TemplateView):
    """WoFlV Wohnflächenübersicht"""

    template_name = "cad_hub/woflv_summary.html"
    partial_template_name = "cad_hub/partials/_woflv_summary.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model_id = self.kwargs["model_id"]

        # Get model and project reference
        ifc_model = get_object_or_404(IFCModel, pk=model_id)

        # Einfache WoFlV-Berechnung aus Räumen
        Room.objects.filter(ifc_model=ifc_model)

        ctx["woflv"] = {
            "wohnflaeche_gesamt": 0,
            "grundflaeche_gesamt": 0,
        }
        ctx["woflv_rooms"] = []
        ctx["ifc_model"] = ifc_model

        return ctx
