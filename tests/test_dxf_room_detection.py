"""
Tests for CADLoaderService room detection (ADR-012 T2).

nl2cad-core's own room-extraction algorithm is validated by nl2cad-core's own
test suite against a real ArchiCAD corpus — these tests check the cad-hub
CONTRACT/WIRING (keys present, values in real m², no raw DXF units leaking
through), not room-detection accuracy.
"""

from pathlib import Path

import pytest

from apps.dxf.services.cad_loader import CADLoaderService

FIXTURE_DXF = Path(__file__).parent / "fixtures" / "dxf" / "real_lageplan_r12.dxf"


@pytest.fixture
def loader():
    return CADLoaderService.from_file(FIXTURE_DXF)


class TestGetRooms:
    def test_should_return_name_position_layer_keys(self, loader):
        rooms = loader.get_rooms()
        assert rooms, "Fixture sollte Räume enthalten"
        for room in rooms:
            assert set(room.keys()) == {"name", "position", "layer"}
            assert isinstance(room["position"], dict)
            assert {"x", "y"} <= set(room["position"].keys())

    def test_should_find_rooms_in_real_lageplan(self, loader):
        rooms = loader.get_rooms()
        assert len(rooms) == 11


class TestGetRoomAreas:
    def test_should_return_area_perimeter_vertex_count_keys(self, loader):
        areas = loader.get_room_areas()
        assert areas, "Fixture sollte Flächen enthalten"
        for area in areas:
            assert set(area.keys()) == {"handle", "layer", "area", "perimeter", "vertex_count"}

    def test_should_return_real_m2_not_raw_dxf_units(self, loader):
        """
        Regression guard: vor ADR-012 T2 waren area/perimeter rohe DXF-Einheiten
        (oft im Millionen-Bereich für mm²). Nach der Migration sind es echte m².
        """
        areas = loader.get_room_areas()
        for area in areas:
            assert 0 < area["area"] < 10_000, (
                f"area={area['area']} sieht nach roher DXF-Einheit aus, nicht m²"
            )
            assert 0 < area["perimeter"] < 1_000

    def test_should_align_positionally_with_get_rooms(self, loader):
        """get_rooms()/get_room_areas() lesen aus derselben dxf_model.rooms-Liste."""
        rooms = loader.get_rooms()
        areas = loader.get_room_areas()
        assert len(rooms) == len(areas)
        for room, area in zip(rooms, areas, strict=True):
            assert room["layer"] == area["layer"]


class TestDxfModel:
    def test_should_cache_dxf_model_across_calls(self, loader):
        model_a = loader.dxf_model
        model_b = loader.dxf_model
        assert model_a is model_b

    def test_should_apply_cadhub_extra_excluded_layer_keywords(self, loader):
        """Wand/Dach/Treppe-Layer dürfen nicht als Raum durchrutschen (Parität zur
        alten _is_excluded_layer-Logik in room_analysis.py)."""
        excluded_substrings = ("wand", "dach", "treppe", "decken")
        for room in loader.dxf_model.rooms:
            layer_lower = room.layer.lower()
            assert not any(kw in layer_lower for kw in excluded_substrings)
