"""
Regression tests: get_room_areas() now returns real m² (ADR-012 T2). These
three call sites used to compensate for raw DXF units themselves — if that
compensating logic isn't removed, they silently divide an already-correct
value again (e.g. m² / 1_000_000), which produces no error, just wrong
numbers. Each test asserts the *correct* (non-double-corrected) output for a
fake loader returning realistic m² values.
"""

from unittest.mock import MagicMock

from apps.ifc.handlers.massen import MassenHandler
from apps.ifc.handlers.nl_query import NLQueryHandler, ParsedQuery, QueryIntent
from apps.ifc.handlers.room_analysis import RoomAnalysisHandler

REAL_M2_AREAS = [
    {"handle": "", "layer": "GEB_HAUPT", "area": 153.38, "perimeter": 53.71, "vertex_count": 15},
    {"handle": "", "layer": "GEB_HAUPT", "area": 50.0, "perimeter": 28.65, "vertex_count": 6},
]
REAL_M2_ROOMS = [
    {"name": "12a", "position": {"x": 0, "y": 0}, "layer": "GEB_HAUPT"},
    {"name": "Raum (GEB_HAUPT)", "position": {"x": 0, "y": 0}, "layer": "GEB_HAUPT"},
]


def _fake_loader():
    loader = MagicMock()
    loader.get_rooms.return_value = REAL_M2_ROOMS
    loader.get_room_areas.return_value = REAL_M2_AREAS
    loader.get_doors.return_value = []
    loader.get_windows.return_value = []
    return loader


class TestRoomAnalysisHandlerNoDoubleCorrection:
    def test_should_keep_area_m2_as_is_not_divide_again(self):
        handler = RoomAnalysisHandler()
        result = handler.execute({"loader": _fake_loader(), "classify_din277": False})
        assert result.success
        areas = sorted(r["area_m2"] for r in result.data["rooms"])
        assert areas == sorted(a["area"] for a in REAL_M2_AREAS)

    def test_should_not_reference_removed_unit_factor_helper(self):
        import apps.ifc.handlers.room_analysis as module

        assert not hasattr(module, "_get_unit_factor")
        assert not hasattr(module, "_is_excluded_layer")
        assert not hasattr(module, "_is_valid_floor_layer")


class TestNlQueryHandlerNoDoubleCorrection:
    def test_should_sum_areas_as_is_not_divide_again(self):
        handler = NLQueryHandler()
        parsed = ParsedQuery(
            original="Gesamtfläche?",
            intent=QueryIntent.TOTAL_AREA,
            entities={},
            confidence=1.0,
        )
        response = handler._generate_response(parsed, _fake_loader(), {})
        expected_total = sum(a["area"] for a in REAL_M2_AREAS)
        assert f"{expected_total:.1f}" in response


class TestMassenHandlerNoDoubleCorrection:
    def test_should_keep_area_m2_as_is_not_divide_again(self):
        handler = MassenHandler()
        category = handler._calculate_floors(_fake_loader(), [], MagicMock())
        values = sorted(item.value for item in category.items)
        assert values == sorted(a["area"] for a in REAL_M2_AREAS)
