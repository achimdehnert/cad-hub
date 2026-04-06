"""AVB Page Header Component (ADR-041)."""

from __future__ import annotations

from typing import Any


def get_context(
    title: str,
    subtitle: str = "",
    icon: str = "bi-building",
    cta_label: str = "",
    cta_url: str = "",
    cta_icon: str = "bi-plus-lg",
) -> dict[str, Any]:
    """Single source of truth for page header data.

    Used by inclusion tag and tests alike.
    """
    return {
        "title": title,
        "subtitle": subtitle,
        "icon": icon,
        "cta_label": cta_label,
        "cta_url": cta_url,
        "cta_icon": cta_icon,
    }
