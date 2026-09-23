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
    # PDF-Handler (Issue #68). PDFVisionHandler bekommt bewusst keinen
    # Endpunkt — er ruft OpenAI/Anthropic direkt und verletzt damit ADR-089;
    # Begruendung im Modul-Docstring von handlers/pdf_vision.py.
    path(
        "pdf/lageplan/",
        views.PDFLageplanAnalyzeView.as_view(),
        name="pdf_lageplan",
    ),
    path(
        "pdf/abstandsflaechen/",
        views.PDFAbstandsflaechenAnalyzeView.as_view(),
        name="pdf_abstandsflaechen",
    ),
    # Der Aufrufer der beiden Endpunkte. Ohne ihn waren sie geroutet und
    # getestet, aber in Produktion nicht nutzbar (403 CSRF) — Issue #68.
    path(
        "pdf/",
        views.PDFAuswertungView.as_view(),
        name="pdf_auswertung",
    ),
]
