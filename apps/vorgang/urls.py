"""Vorgang URL configuration (#72 K4)."""

from django.urls import path

from . import views

app_name = "vorgang"

urlpatterns = [
    path("", views.VorgangListView.as_view(), name="vorgang_list"),
    path("neu/", views.VorgangCreateView.as_view(), name="vorgang_create"),
    path("<uuid:pk>/", views.VorgangDetailView.as_view(), name="vorgang_detail"),
    path("<uuid:pk>/dokument/", views.DokumentUploadView.as_view(), name="dokument_upload"),
    path("befund/<uuid:pk>/status/", views.BefundStatusView.as_view(), name="befund_status"),
]
