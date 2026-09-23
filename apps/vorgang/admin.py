"""Vorgang admin (#72 K4)."""

from django.contrib import admin

from .models import Befund, Dokument, Vorgang


@admin.register(Vorgang)
class VorgangAdmin(admin.ModelAdmin):
    list_display = [
        "titel",
        "art",
        "eingereicht_von_rolle",
        "status",
        "tenant_id",
        "loeschfrist_am",
        "created_at",
    ]
    list_filter = ["art", "eingereicht_von_rolle", "status"]
    search_fields = ["titel"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Dokument)
class DokumentAdmin(admin.ModelAdmin):
    list_display = [
        "dateiname",
        "vorgang",
        "vorlagenart",
        "seiten",
        "tenant_id",
        "created_at",
    ]
    list_filter = ["vorlagenart"]
    search_fields = ["dateiname", "sha256"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(Befund)
class BefundAdmin(admin.ModelAdmin):
    list_display = [
        "regel_id",
        "feld",
        "status",
        "vorgang",
        "dokument",
        "tenant_id",
        "created_at",
    ]
    list_filter = ["status", "regel_id"]
    search_fields = ["regel_id", "feld"]
    readonly_fields = ["id", "created_at", "updated_at"]
