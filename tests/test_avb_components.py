"""
Tests for AVB Component inclusion tags (ADR-041).

Verifies that get_context() functions return the correct data
for the three AVB UI components.
"""

import pytest

# ---------------------------------------------------------------------------
# page_header component
# ---------------------------------------------------------------------------


def test_page_header_get_context_defaults():
    from apps.avb.components.page_header import get_context

    ctx = get_context("Bauprojekte")
    assert ctx["title"] == "Bauprojekte"
    assert ctx["subtitle"] == ""
    assert ctx["icon"] == "bi-building"
    assert ctx["cta_label"] == ""
    assert ctx["cta_url"] == ""
    assert ctx["cta_icon"] == "bi-plus-lg"


def test_page_header_get_context_with_cta():
    from apps.avb.components.page_header import get_context

    ctx = get_context(
        "Ausschreibungen",
        subtitle="Übersicht",
        icon="bi-file-earmark-text",
        cta_label="Neu",
        cta_url="/avb/tenders/create/",
    )
    assert ctx["title"] == "Ausschreibungen"
    assert ctx["subtitle"] == "Übersicht"
    assert ctx["cta_label"] == "Neu"
    assert ctx["cta_url"] == "/avb/tenders/create/"


# ---------------------------------------------------------------------------
# stat_card component
# ---------------------------------------------------------------------------


def test_stat_card_get_context_defaults():
    from apps.avb.components.stat_card import get_context

    ctx = get_context(42, "Gesamt")
    assert ctx["value"] == 42
    assert ctx["label"] == "Gesamt"
    assert ctx["icon"] == "bi-bar-chart"
    assert ctx["variant"] == "primary"


def test_stat_card_get_context_variant():
    from apps.avb.components.stat_card import get_context

    ctx = get_context(5, "Vergeben", icon="bi-check-circle", variant="success")
    assert ctx["variant"] == "success"


def test_stat_card_invalid_variant_falls_back_to_primary():
    from apps.avb.components.stat_card import get_context

    ctx = get_context(0, "Label", variant="invalid-variant")
    assert ctx["variant"] == "primary"


# ---------------------------------------------------------------------------
# empty_state component
# ---------------------------------------------------------------------------


def test_empty_state_get_context_defaults():
    from apps.avb.components.empty_state import get_context

    ctx = get_context("Keine Projekte")
    assert ctx["title"] == "Keine Projekte"
    assert ctx["message"] == ""
    assert ctx["icon"] == "bi-inbox"
    assert ctx["cta_label"] == ""
    assert ctx["cta_url"] == ""


def test_empty_state_get_context_with_cta():
    from apps.avb.components.empty_state import get_context

    ctx = get_context(
        "Noch keine Bauprojekte",
        message="Starten Sie Ihr erstes Bauvorhaben",
        icon="bi-building",
        cta_label="Projekt erstellen",
        cta_url="/avb/projects/create/",
    )
    assert ctx["title"] == "Noch keine Bauprojekte"
    assert ctx["message"] == "Starten Sie Ihr erstes Bauvorhaben"
    assert ctx["cta_label"] == "Projekt erstellen"
    assert ctx["cta_url"] == "/avb/projects/create/"
