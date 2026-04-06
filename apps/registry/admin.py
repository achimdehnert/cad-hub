"""
Registry Admin — Modul-Katalog, Berufsprofile, Subscriptions.

Vollständig über Django Admin pflegbar:
- Module + Preise anlegen / bearbeiten
- Berufsprofile mit Modul-Zuordnung konfigurieren
- Tenant-Subscriptions verwalten + aktivieren
- Rabatt-Regeln definieren
"""

from decimal import Decimal

from django.contrib import admin
from django.db.models import QuerySet, Sum
from django.http import HttpRequest
from django.utils.html import format_html

from .models import (
    BerufsProfil,
    DiscountRule,
    ModulePricing,
    NL2CADModule,
    ProfilModuleMapping,
    TenantSubscription,
)

# ─────────────────────────────────────────────────────────────────────────────
# INLINE: Preise direkt am Modul
# ─────────────────────────────────────────────────────────────────────────────


class ModulePricingInline(admin.TabularInline):
    model = ModulePricing
    extra = 1
    fields = [
        "organization",
        "pricing_type",
        "setup_eur",
        "monthly_eur",
        "label",
        "valid_from",
        "valid_until",
    ]
    readonly_fields = ["created_at"]


class ProfilModuleMappingInline(admin.TabularInline):
    model = ProfilModuleMapping
    extra = 2
    fields = ["module", "mapping_type", "is_recommended"]
    autocomplete_fields = ["module"]


class SubscriptionInline(admin.TabularInline):
    model = TenantSubscription
    extra = 0
    fields = ["module", "status", "monthly_eur", "activated_at", "approved_by"]
    readonly_fields = ["activated_at", "created_at"]
    show_change_link = True


# ─────────────────────────────────────────────────────────────────────────────
# MODUL-ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(NL2CADModule)
class NL2CADModuleAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "icon_display",
        "package",
        "status_badge",
        "priority",
        "story_points",
        "target_quarter",
        "standard_price_display",
        "subscription_count",
    ]
    list_filter = ["status", "priority", "is_required"]
    search_fields = ["id", "package", "name", "tagline"]
    ordering = ["sort_order", "id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ModulePricingInline]

    fieldsets = [
        (
            "Identifikation",
            {
                "fields": ["id", "package", "name", "icon", "color", "tagline", "sort_order"],
            },
        ),
        (
            "Inhalt",
            {
                "fields": ["description", "features", "deps", "norms", "main_classes"],
            },
        ),
        (
            "Status & Roadmap",
            {
                "fields": ["is_required", "status", "priority", "story_points", "target_quarter"],
            },
        ),
        (
            "Verknüpfungen",
            {
                "fields": ["adr_path", "workflow_path", "pypi_url"],
                "classes": ["collapse"],
            },
        ),
        (
            "Metadaten",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def icon_display(self, obj: NL2CADModule) -> str:
        return format_html('<span style="font-size:1.4em;">{}</span>', obj.icon)

    icon_display.short_description = ""

    def status_badge(self, obj: NL2CADModule) -> str:
        colors = {
            "stable": "#059669",
            "beta": "#f59e0b",
            "planned": "#f97316",
            "deprecated": "#6b7280",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;'
            'font-size:0.8em;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def standard_price_display(self, obj: NL2CADModule) -> str:
        p = obj.standard_pricing
        if not p:
            return "—"
        if p.monthly_eur == 0:
            return format_html('<span style="color:#059669;">Inklusive</span>')
        return f"{p.monthly_eur:.0f} €/Monat"

    standard_price_display.short_description = "Standardpreis"

    def subscription_count(self, obj: NL2CADModule) -> int:
        return obj.subscriptions.filter(status="active").count()

    subscription_count.short_description = "Aktive Subs"


@admin.register(ModulePricing)
class ModulePricingAdmin(admin.ModelAdmin):
    list_display = [
        "module",
        "organization",
        "pricing_type",
        "setup_eur",
        "monthly_eur",
        "label",
        "valid_from",
        "valid_until",
    ]
    list_filter = ["pricing_type", "module__status"]
    search_fields = ["module__id", "module__name", "organization__name"]
    autocomplete_fields = ["module"]


# ─────────────────────────────────────────────────────────────────────────────
# BERUFSPROFIL-ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(BerufsProfil)
class BerufsProfilAdmin(admin.ModelAdmin):
    list_display = ["icon", "id", "name", "fokus", "bereitschaft", "module_count", "sort_order"]
    search_fields = ["id", "name", "fokus"]
    ordering = ["sort_order", "name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ProfilModuleMappingInline]

    fieldsets = [
        (
            "Identifikation",
            {
                "fields": ["id", "name", "icon", "fokus", "bereitschaft", "sort_order"],
            },
        ),
        (
            "Konfiguration",
            {
                "fields": ["install_command", "yaml_config"],
            },
        ),
        (
            "NLP & Report",
            {
                "fields": ["nlp_keywords", "report_template", "primary_output"],
            },
        ),
        (
            "Metadaten",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def module_count(self, obj: BerufsProfil) -> str:
        total = obj.profilmodulemapping_set.count()
        recommended = obj.profilmodulemapping_set.filter(is_recommended=True).count()
        return f"{recommended} empf. / {total} gesamt"

    module_count.short_description = "Module"


@admin.register(ProfilModuleMapping)
class ProfilModuleMappingAdmin(admin.ModelAdmin):
    list_display = ["profil", "module", "mapping_type", "is_recommended"]
    list_filter = ["mapping_type", "is_recommended", "profil"]
    search_fields = ["profil__name", "module__name"]
    autocomplete_fields = ["module"]


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION-ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "organization",
        "module",
        "status_badge",
        "monthly_eur",
        "berufsprofil",
        "approved_by",
        "activated_at",
        "created_at",
    ]
    list_filter = ["status", "module", "berufsprofil"]
    search_fields = ["organization__name", "module__id", "approved_by"]
    readonly_fields = ["id", "tenant_id", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = [
        (
            "Tenant & Modul",
            {
                "fields": ["organization", "module", "berufsprofil"],
            },
        ),
        (
            "Status & Preise",
            {
                "fields": ["status", "monthly_eur", "setup_eur", "trial_until"],
            },
        ),
        (
            "Freigabe",
            {
                "fields": ["approved_by", "activated_at", "cancelled_at", "notes"],
            },
        ),
        (
            "Metadaten",
            {
                "fields": ["id", "tenant_id", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    actions = ["activate_subscriptions", "suspend_subscriptions"]

    def status_badge(self, obj: TenantSubscription) -> str:
        colors = {
            "pending": "#f59e0b",
            "trial": "#0891b2",
            "active": "#059669",
            "suspended": "#dc2626",
            "cancelled": "#6b7280",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:0.8em;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    @admin.action(description="Ausgewählte Subscriptions aktivieren + Onboarding triggern")
    def activate_subscriptions(
        self, request: HttpRequest, queryset: QuerySet[TenantSubscription]
    ) -> None:
        from django.utils import timezone

        from .signals import _trigger_onboarding_workflow

        to_activate = list(queryset.filter(status__in=["pending", "trial"]))
        for sub in to_activate:
            sub.status = "active"
            sub.activated_at = timezone.now()
            sub._trigger_workflow = True
            sub.save()

        if to_activate:
            # Einmal pro Organisation triggern (nicht je Modul)
            orgs_done: set = set()
            for sub in to_activate:
                if sub.organization_id not in orgs_done:
                    _trigger_onboarding_workflow(sub)
                    orgs_done.add(sub.organization_id)

        self.message_user(
            request,
            f"{len(to_activate)} Subscription(s) aktiviert"
            + (
                f" — Onboarding-Workflow für {len(orgs_done)} Organisation(en) getriggert."
                if to_activate
                else "."
            ),
        )

    @admin.action(description="Ausgewählte Subscriptions sperren")
    def suspend_subscriptions(
        self, request: HttpRequest, queryset: QuerySet[TenantSubscription]
    ) -> None:
        updated = queryset.filter(status="active").update(status="suspended")
        self.message_user(request, f"{updated} Subscription(s) gesperrt.")


# ─────────────────────────────────────────────────────────────────────────────
# RABATT-ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "min_modules", "discount_percent", "is_active"]
    list_filter = ["is_active"]
