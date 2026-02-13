"""DXF URL configuration."""
from django.urls import path

from . import views

app_name = "dxf"

urlpatterns = [
    path(
        "",
        views.DXFViewerView.as_view(),
        name="dxf_viewer",
    ),
    path(
        "upload/",
        views.DXFUploadView.as_view(),
        name="dxf_upload",
    ),
    path(
        "render-svg/",
        views.DXFRenderSVGView.as_view(),
        name="dxf_render_svg",
    ),
    path(
        "parse/",
        views.DXFParseView.as_view(),
        name="dxf_parse",
    ),
    path(
        "nl2dxf/",
        views.NL2DXFView.as_view(),
        name="nl2dxf",
    ),
    path(
        "nl2dxf/generate/",
        views.NL2DXFGenerateView.as_view(),
        name="nl2dxf_generate",
    ),
    path(
        "download/",
        views.DXFDownloadView.as_view(),
        name="dxf_download",
    ),
    # DXF Analyse
    path(
        "analyze/",
        views.DXFAnalysisView.as_view(),
        name="dxf_analysis",
    ),
    path(
        "analyze/upload/",
        views.DXFAnalyzeUploadView.as_view(),
        name="dxf_analyze_upload",
    ),
    path(
        "api/layers/",
        views.DXFLayersAPIView.as_view(),
        name="dxf_api_layers",
    ),
    path(
        "api/blocks/",
        views.DXFBlocksAPIView.as_view(),
        name="dxf_api_blocks",
    ),
    path(
        "api/texts/",
        views.DXFTextsAPIView.as_view(),
        name="dxf_api_texts",
    ),
    path(
        "api/dimensions/",
        views.DXFDimensionsAPIView.as_view(),
        name="dxf_api_dimensions",
    ),
    path(
        "api/rooms/",
        views.DXFRoomsAPIView.as_view(),
        name="dxf_api_rooms",
    ),
    path(
        "export/json/",
        views.DXFExportJSONView.as_view(),
        name="dxf_export_json",
    ),
    path(
        "dwg-status/",
        views.DWGStatusView.as_view(),
        name="dwg_status",
    ),
]
