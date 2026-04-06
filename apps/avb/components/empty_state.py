"""AVB Empty State Component (ADR-041)."""

from __future__ import annotations

from typing import Any


def get_context(
    title: str,
    message: str = "",
    icon: str = "bi-inbox",
    cta_label: str = "",
    cta_url: str = "",
    cta_icon: str = "bi-plus-lg",
) -> dict[str, Any]:
    """Single source of truth for empty state data."""
    return {
        "title": title,
        "message": message,
        "icon": icon,
        "cta_label": cta_label,
        "cta_url": cta_url,
        "cta_icon": cta_icon,
    }
