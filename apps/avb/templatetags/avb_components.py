"""Component inclusion tags for AVB templates (ADR-041)."""

from __future__ import annotations

from django import template

register = template.Library()


@register.inclusion_tag(
    "avb/components/_page_header.html",
    takes_context=False,
)
def avb_page_header(
    title: str,
    subtitle: str = "",
    icon: str = "bi-building",
    cta_label: str = "",
    cta_url: str = "",
    cta_icon: str = "bi-plus-lg",
) -> dict:
    """Render AVB page header with optional CTA button.

    Usage::

        {% load avb_components %}
        {% avb_page_header "Bauprojekte" subtitle="Übersicht" icon="bi-building" cta_label="Neu" cta_url=create_url %}
    """
    from apps.avb.components.page_header import get_context

    return get_context(
        title=title,
        subtitle=subtitle,
        icon=icon,
        cta_label=cta_label,
        cta_url=cta_url,
        cta_icon=cta_icon,
    )


@register.inclusion_tag(
    "avb/components/_stat_card.html",
    takes_context=False,
)
def avb_stat_card(
    value,
    label: str,
    icon: str = "bi-bar-chart",
    variant: str = "primary",
) -> dict:
    """Render a stat card with icon, value and label.

    Usage::

        {% load avb_components %}
        {% avb_stat_card tenders.count "Gesamt" icon="bi-file-text" variant="primary" %}
        {% avb_stat_card open_count "Offen" icon="bi-hourglass-split" variant="warning" %}
    """
    from apps.avb.components.stat_card import get_context

    return get_context(value=value, label=label, icon=icon, variant=variant)


@register.inclusion_tag(
    "avb/components/_empty_state.html",
    takes_context=False,
)
def avb_empty_state(
    title: str,
    message: str = "",
    icon: str = "bi-inbox",
    cta_label: str = "",
    cta_url: str = "",
    cta_icon: str = "bi-plus-lg",
) -> dict:
    """Render an empty state with icon, title, message and optional CTA.

    Usage::

        {% load avb_components %}
        {% avb_empty_state "Noch keine Projekte" message="Starten Sie..." icon="bi-building" cta_label="Erstellen" cta_url=create_url %}
    """
    from apps.avb.components.empty_state import get_context

    return get_context(
        title=title,
        message=message,
        icon=icon,
        cta_label=cta_label,
        cta_url=cta_url,
        cta_icon=cta_icon,
    )
