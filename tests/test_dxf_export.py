"""
Tests for DXF export with layer selection (Issue #2).
"""

import io
import uuid

import pytest

from apps.ifc.services.dxf_export_service import (
    EXPORT_LAYERS,
    DXFExportLayer,
    export_ifc_to_dxf,
    get_available_layers,
)


class TestGetAvailableLayers:
    """Tests for get_available_layers service function."""

    def test_should_return_all_defined_layers(self):
        """All defined export layers should be returned."""
        # We can't easily test with a real model without DB,
        # but we can verify the layer definitions
        assert len(EXPORT_LAYERS) == 8

    def test_should_have_correct_layer_keys(self):
        expected_keys = {
            "walls_external",
            "walls_internal",
            "rooms",
            "doors",
            "windows",
            "slabs",
            "dimensions",
            "text",
        }
        assert set(EXPORT_LAYERS.keys()) == expected_keys

    def test_should_have_autocad_layer_naming(self):
        """Layer names should follow AIA naming convention (A-*)."""
        for key, layer in EXPORT_LAYERS.items():
            assert layer.name.startswith("A-"), f"Layer {key} name should start with A-"

    def test_should_have_unique_colors(self):
        """Each layer should have a distinct color."""
        colors = [l.color for l in EXPORT_LAYERS.values()]
        assert len(colors) == len(set(colors)), "Layer colors should be unique"

    def test_should_have_descriptions(self):
        """All layers should have German descriptions."""
        for key, layer in EXPORT_LAYERS.items():
            assert layer.description, f"Layer {key} missing description"
            assert len(layer.description) > 3


class TestExportLayers:
    """Tests for DXFExportLayer dataclass."""

    def test_should_create_layer_with_defaults(self):
        layer = DXFExportLayer(
            key="test",
            name="A-TEST",
            description="Test layer",
            color=1,
        )
        assert layer.entity_count == 0

    def test_should_store_entity_count(self):
        layer = DXFExportLayer(
            key="test",
            name="A-TEST",
            description="Test layer",
            color=1,
            entity_count=42,
        )
        assert layer.entity_count == 42
