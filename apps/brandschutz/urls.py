"""Brandschutz URL configuration."""
from django.urls import path

from . import views

app_name = "brandschutz"

urlpatterns = [
    # Dashboard
    path(
        "",
        views.BrandschutzDashboardView.as_view(),
        name="dashboard",
    ),
    # Prüfungen
    path(
        "pruefungen/",
        views.BrandschutzPruefungListView.as_view(),
        name="pruefung_list",
    ),
    path(
        "pruefungen/neu/",
        views.BrandschutzPruefungCreateView.as_view(),
        name="pruefung_create",
    ),
    path(
        "pruefungen/<uuid:pk>/",
        views.BrandschutzPruefungDetailView.as_view(),
        name="pruefung_detail",
    ),
    path(
        "pruefungen/<uuid:pk>/bearbeiten/",
        views.BrandschutzPruefungUpdateView.as_view(),
        name="pruefung_edit",
    ),
    # Analyse
    path(
        "analyse/",
        views.BrandschutzAnalyseView.as_view(),
        name="analyse",
    ),
    path(
        "analyse/<uuid:pk>/",
        views.BrandschutzAnalyseView.as_view(),
        name="analyse_pruefung",
    ),
    # Reports
    path(
        "pruefungen/<uuid:pk>/report/",
        views.BrandschutzReportView.as_view(),
        name="report_html",
    ),
    path(
        "pruefungen/<uuid:pk>/report/pdf/",
        views.BrandschutzReportView.as_view(),
        {"format": "pdf"},
        name="report_pdf",
    ),
    path(
        "pruefungen/<uuid:pk>/report/excel/",
        views.BrandschutzReportView.as_view(),
        {"format": "excel"},
        name="report_excel",
    ),
    path(
        "pruefungen/<uuid:pk>/report/json/",
        views.BrandschutzReportView.as_view(),
        {"format": "json"},
        name="report_json",
    ),
    # HTMX Partials
    path(
        "maengel/<uuid:pk>/toggle/",
        views.BrandschutzMangelToggleView.as_view(),
        name="mangel_toggle",
    ),
    path(
        "symbole/<uuid:pk>/approve/",
        views.BrandschutzSymbolApproveView.as_view(),
        name="symbol_approve",
    ),
    # Regelwerke
    path(
        "regelwerke/",
        views.BrandschutzRegelwerkListView.as_view(),
        name="regelwerk_list",
    ),
    # API
    path(
        "api/stats/",
        views.BrandschutzStatsAPIView.as_view(),
        name="api_stats",
    ),
    path(
        "api/search/",
        views.BrandschutzSearchAPIView.as_view(),
        name="api_search",
    ),
]
