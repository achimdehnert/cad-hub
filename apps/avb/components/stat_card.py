"""AVB Stat Card Component (ADR-041)."""

from __future__ import annotations

from typing import Any

VARIANTS = ("primary", "success", "warning", "danger")


def get_context(
    value: Any,
    label: str,
    icon: str = "bi-bar-chart",
    variant: str = "primary",
) -> dict[str, Any]:
    """Single source of truth for stat card data."""
    if variant not in VARIANTS:
        variant = "primary"
    return {
        "value": value,
        "label": label,
        "icon": icon,
        "variant": variant,
    }
