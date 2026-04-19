"""
Registry Service Layer (ADR-041).

Encapsulates ORM queries for the Registry module API.
"""

from ..models import BerufsProfil, DiscountRule, NL2CADModule, ProfilModuleMapping


def get_modules_ordered():
    """All modules with pricing, ordered."""
    return NL2CADModule.objects.prefetch_related("pricing_tiers").order_by("sort_order", "id")


def get_active_discount() -> DiscountRule | None:
    """First active discount rule."""
    return DiscountRule.objects.filter(is_active=True).order_by("min_modules").first()


def get_profiles_ordered():
    """All profiles ordered."""
    return BerufsProfil.objects.all().order_by("sort_order", "name")


def get_profile_mappings(profil: BerufsProfil):
    """Module mappings for a profile."""
    return (
        ProfilModuleMapping.objects.filter(profil=profil)
        .select_related("module")
        .order_by("module__sort_order")
    )


def get_branches() -> list[dict]:
    """Profiles as 'branches' for configurator backward compat."""
    profiles = BerufsProfil.objects.prefetch_related("profilmodulemapping_set").order_by(
        "sort_order"
    )
    result = []
    for bp in profiles:
        recommended = [m.module_id for m in bp.profilmodulemapping_set.filter(is_recommended=True)]
        result.append(
            {
                "id": bp.id,
                "label": bp.name,
                "icon": bp.icon,
                "recommended_modules": recommended,
                "description": bp.fokus,
                "bereitschaft": bp.bereitschaft,
            }
        )
    return result
