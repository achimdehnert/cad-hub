"""
DXF Export Views — Layer selection UI + download (Issue #2).
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import TenantMixin

from .models import IFCModel
from .services.dxf_export_service import (
    export_ifc_to_dxf,
    get_available_layers,
)

logger = logging.getLogger(__name__)


class DXFExportView(TenantMixin, LoginRequiredMixin, TemplateView):
    """Layer selection form for DXF export."""

    template_name = "cad_hub/dxf_export.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tid = self._tenant_id()
        ifc_model = get_object_or_404(IFCModel, pk=self.kwargs["model_id"], tenant_id=tid)
        ctx["ifc_model"] = ifc_model
        ctx["project"] = ifc_model.project
        ctx["layers"] = get_available_layers(ifc_model)
        ctx["floors"] = ifc_model.floors.order_by("sort_order")
        return ctx


class DXFExportDownloadView(TenantMixin, LoginRequiredMixin, View):
    """Generate and download DXF file with selected layers.

    POST /ifc/model/<uuid>/export/dxf/download/
    Form params:
        layers[]: list of layer keys
        floor: optional floor PK
    """

    def post(self, request, model_id):
        tid = self._tenant_id()
        ifc_model = get_object_or_404(IFCModel, pk=model_id, tenant_id=tid)

        selected_layers = request.POST.getlist("layers")
        floor_id = request.POST.get("floor") or None

        if not selected_layers:
            selected_layers = ["walls_external", "walls_internal", "rooms", "text"]

        output = export_ifc_to_dxf(
            ifc_model=ifc_model,
            selected_layers=selected_layers,
            floor_id=floor_id,
        )

        filename = f"{ifc_model.project.name}_v{ifc_model.version}.dxf"
        filename = filename.replace(" ", "_")

        response = HttpResponse(
            output.read(),
            content_type="application/dxf",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
