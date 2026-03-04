"""
Registry API Views.

GET /api/registry/modules/   — Modul-Liste (abwärtskompatibel zu modules.json)
GET /api/registry/profiles/  — Berufsprofile
GET /api/registry/config/    — Discount-Regeln + Metadaten
"""
import json
import logging
from decimal import Decimal

from django.http import JsonResponse
from django.views import View

from .models import BerufsProfil, DiscountRule, NL2CADModule, ProfilModuleMapping

logger = logging.getLogger(__name__)


def _serialize_module(m: NL2CADModule) -> dict:
    p = m.standard_pricing
    return {
        "id":           m.id,
        "package":      m.package,
        "name":         m.name,
        "icon":         m.icon,
        "color":        m.color,
        "tagline":      m.tagline,
        "description":  m.description,
        "features":     m.features,
        "deps":         m.deps,
        "norms":        m.norms,
        "required":     m.is_required,
        "status":       m.status,
        "priority":     m.priority,
        "story_points": m.story_points,
        "target_quarter": m.target_quarter,
        "adr":          m.adr_path or None,
        "workflow":     m.workflow_path or None,
        "pypi":         m.pypi_url or None,
        "pricing": {
            "setup_eur":   float(p.setup_eur)   if p else 0,
            "monthly_eur": float(p.monthly_eur) if p else 0,
            "label":       p.label              if p else "",
        },
    }


def _serialize_profile(bp: BerufsProfil) -> dict:
    mappings = (
        ProfilModuleMapping.objects
        .filter(profil=bp)
        .select_related("module")
        .order_by("module__sort_order")
    )
    return {
        "id":             bp.id,
        "name":           bp.name,
        "icon":           bp.icon,
        "fokus":          bp.fokus,
        "bereitschaft":   bp.bereitschaft,
        "install":        bp.install_command,
        "yaml_config":    bp.yaml_config,
        "nlp_keywords":   bp.nlp_keywords_list,
        "report_template": bp.report_template,
        "primary_output": bp.primary_output,
        "modules": [
            {
                "id":           m.module_id,
                "mapping_type": m.mapping_type,
                "recommended":  m.is_recommended,
            }
            for m in mappings
            if m.mapping_type != "nicht"
        ],
        "recommended_modules": [
            m.module_id for m in mappings if m.is_recommended
        ],
    }


class ModuleListView(View):
    """
    GET /api/registry/modules/

    Gibt Module im Format zurück, das der nl2cad-Konfigurator erwartet.
    Abwärtskompatibel zu docs/data/modules.json.
    """

    def get(self, request) -> JsonResponse:
        modules = (
            NL2CADModule.objects
            .prefetch_related("pricing_tiers")
            .order_by("sort_order", "id")
        )

        discount = DiscountRule.objects.filter(is_active=True).order_by("min_modules").first()

        data = {
            "version":            "2.0.0",
            "product":            "nl2cad",
            "currency":           "EUR",
            "discount_threshold": discount.min_modules      if discount else 3,
            "discount_percent":   float(discount.discount_percent) if discount else 15,
            "modules":            [_serialize_module(m) for m in modules],
            "branches":           _get_branches(),
        }
        return JsonResponse(data)


class ProfileListView(View):
    """
    GET /api/registry/profiles/

    Gibt alle Berufsprofile mit Modul-Zuordnungen zurück.
    """

    def get(self, request) -> JsonResponse:
        profiles = BerufsProfil.objects.all().order_by("sort_order", "name")
        return JsonResponse({"profiles": [_serialize_profile(bp) for bp in profiles]})


class RegistryConfigView(View):
    """
    GET /api/registry/config/

    Gibt Metadaten: Discount-Regeln, Versionsnummer.
    """

    def get(self, request) -> JsonResponse:
        discount = DiscountRule.objects.filter(is_active=True).order_by("min_modules").first()
        return JsonResponse({
            "version":            "2.0.0",
            "discount_threshold": discount.min_modules      if discount else 3,
            "discount_percent":   float(discount.discount_percent) if discount else 15,
        })


def _get_branches() -> list[dict]:
    """Berufsprofile als 'branches' für Konfigurator-Abwärtskompatibilität."""
    profiles = BerufsProfil.objects.prefetch_related(
        "profilmodulemapping_set"
    ).order_by("sort_order")
    result = []
    for bp in profiles:
        recommended = [
            m.module_id
            for m in bp.profilmodulemapping_set.filter(is_recommended=True)
        ]
        result.append({
            "id":                  bp.id,
            "label":               bp.name,
            "icon":                bp.icon,
            "recommended_modules": recommended,
            "description":         bp.fokus,
            "bereitschaft":        bp.bereitschaft,
        })
    return result
