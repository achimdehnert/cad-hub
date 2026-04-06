"""
Static Manifest Completeness Tests (ADR-040 Stufe 1) — cad-hub.

Prüft ob alle data-testid aus den UI-Manifesten in den Templates vorhanden sind.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = BASE_DIR / "templates"
MANIFESTS_DIR = BASE_DIR / "ui-manifests"


def _load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _collect_required_elements(manifest: dict) -> list[dict]:
    elements = []
    for component in manifest.get("components", []):
        component_conditional = bool(component.get("conditional"))
        for el in component.get("required_elements", []):
            el_conditional = bool(el.get("conditional")) or component_conditional
            elements.append(
                {
                    "element_id": el["element_id"],
                    "description": el.get("description", ""),
                    "component": component["id"],
                    "conditional": el_conditional,
                }
            )
    return elements


def _testid_exists_in_templates(element_id: str, template_file: str | None = None) -> bool:
    needle = f'data-testid="{element_id}"'
    if template_file:
        target = TEMPLATES_DIR / template_file
        if target.exists():
            return needle in target.read_text(encoding="utf-8")
    for tmpl in TEMPLATES_DIR.rglob("*.html"):
        if needle in tmpl.read_text(encoding="utf-8"):
            return True
    return False


def _manifest_params():
    params = []
    for manifest_path in sorted(MANIFESTS_DIR.glob("*.yaml")):
        manifest = _load_manifest(manifest_path)
        template_file = manifest.get("page", {}).get("template")
        page_route = manifest.get("page", {}).get("route", manifest_path.name)
        for el in _collect_required_elements(manifest):
            params.append(
                pytest.param(
                    el["element_id"],
                    template_file,
                    el["conditional"],
                    id=f"{page_route}::{el['element_id']}",
                )
            )
    return params


@pytest.mark.parametrize("element_id,template_file,conditional", _manifest_params())
def test_data_testid_present_in_templates(element_id: str, template_file: str, conditional: bool):
    """Every required element_id from UI-Manifest must have data-testid in templates."""
    if conditional:
        pytest.skip(f"Conditional element '{element_id}' — skipped in static check")
    found = _testid_exists_in_templates(element_id, template_file)
    assert found, (
        f'Missing: data-testid="{element_id}" not found in templates.\n'
        f"Template: {template_file or 'any'}\n"
        f'Fix: Add data-testid="{element_id}" to the relevant template.'
    )
