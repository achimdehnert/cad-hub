"""
IFC Upload Views — Drag-and-Drop UI + AJAX API.

Issue #1: Add IFC file upload with drag-and-drop UI.
"""

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import TenantMixin

from .models import IFCModel, IFCProject
from .services.upload_service import (
    UploadValidationError,
    create_ifc_model_from_upload,
    validate_ifc_file,
)

logger = logging.getLogger(__name__)


class IFCUploadView(TenantMixin, LoginRequiredMixin, TemplateView):
    """Drag-and-drop IFC upload page."""

    template_name = "cad_hub/ifc_upload.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tid = self._tenant_id()
        ctx["project"] = get_object_or_404(
            IFCProject, pk=self.kwargs["project_id"], tenant_id=tid
        )
        return ctx


class IFCUploadAPIView(TenantMixin, LoginRequiredMixin, View):
    """AJAX endpoint for IFC file upload.

    POST /ifc/project/<uuid>/upload/api/
    Returns JSON with upload result or error.
    """

    def post(self, request, project_id):
        tid = self._tenant_id()
        project = get_object_or_404(IFCProject, pk=project_id, tenant_id=tid)

        file = request.FILES.get("ifc_file")

        try:
            validate_ifc_file(file)
        except UploadValidationError as e:
            return JsonResponse(
                {"success": False, "error": e.message, "code": e.code},
                status=400,
            )

        try:
            ifc_model = create_ifc_model_from_upload(
                project=project,
                file=file,
                tenant_id=tid,
            )
        except Exception as e:
            logger.exception("Upload failed: %s", e)
            return JsonResponse(
                {
                    "success": False,
                    "error": "Upload fehlgeschlagen. Bitte versuchen Sie es erneut.",
                    "code": "server_error",
                },
                status=500,
            )

        return JsonResponse(
            {
                "success": True,
                "model_id": str(ifc_model.pk),
                "version": ifc_model.version,
                "status": ifc_model.status,
                "redirect_url": f"/ifc/model/{ifc_model.pk}/",
            }
        )


class IFCUploadStatusAPIView(TenantMixin, LoginRequiredMixin, View):
    """Poll upload processing status.

    GET /ifc/model/<uuid>/status/
    Returns JSON with current processing status.
    """

    def get(self, request, pk):
        tid = self._tenant_id()
        ifc_model = get_object_or_404(IFCModel, pk=pk, tenant_id=tid)

        data = {
            "status": ifc_model.status,
            "status_display": ifc_model.get_status_display(),
            "error_message": ifc_model.error_message or "",
        }

        if ifc_model.status == IFCModel.Status.READY:
            data["redirect_url"] = f"/ifc/model/{ifc_model.pk}/"
            data["stats"] = {
                "floors": ifc_model.floors.count(),
                "rooms": ifc_model.rooms.count(),
            }

        return JsonResponse(data)
