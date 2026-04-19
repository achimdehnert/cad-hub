# apps/cad_hub/views.py
"""
Views für IFC Dashboard
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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

from .models import IFCModel, IFCProject, Room
from .services.ifc_query_service import (
    extract_ifc_data,
    get_area_summary,
    get_dashboard_stats,
    get_floors_for_model,
    get_floors_with_stats,
    get_model_content_stats,
    get_model_floor_stats,
    get_next_version,
    get_recent_projects,
    get_rooms_queryset,
)


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


class DashboardView(LoginRequiredMixin, TenantMixin, TemplateView):
    """Haupt-Dashboard mit Übersicht"""

    template_name = "cad_hub/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tid = self._tenant_id()
        ctx["recent_projects"] = get_recent_projects(tid)
        ctx["stats"] = get_dashboard_stats(tid)
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
        ctx["floors"] = get_model_floor_stats(model)
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

        ctx["stats"] = get_model_content_stats(model)
        ctx["floors_with_stats"] = get_floors_with_stats(model)

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

        form.instance.tenant_id = tid
        form.instance.project = project
        form.instance.version = get_next_version(project)
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
        return get_rooms_queryset(
            model_id=self.kwargs["model_id"],
            floor_id=self.request.GET.get("floor"),
            usage=self.request.GET.get("usage"),
            search=self.request.GET.get("q"),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model_id = self.kwargs["model_id"]

        ctx["ifc_model"] = get_object_or_404(IFCModel, pk=model_id)
        ctx["floors"] = get_floors_for_model(model_id)
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

        summary = get_area_summary(ifc_model)
        ctx["areas"] = summary["areas"]
        ctx["din277"] = summary["din277"]
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

        # WoFlV placeholder (no calculation yet)

        ctx["woflv"] = {
            "wohnflaeche_gesamt": 0,
            "grundflaeche_gesamt": 0,
        }
        ctx["woflv_rooms"] = []
        ctx["ifc_model"] = ifc_model

        return ctx
