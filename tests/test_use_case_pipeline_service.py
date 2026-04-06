"""
Tests für UseCasePipelineService (ADR-085) — cad-hub.

Kein Django-DB nötig. Testet:
- Direct-Mode (orchestrator_mcp im PYTHONPATH)
- HTTP-Mode (httpx mock)
- Stub-Fallback
- Singleton get_pipeline_service()
- health_check()
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from apps.core.services.use_case_pipeline_service import (
    UseCasePipelineService,
    get_pipeline_service,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _pipeline_payload() -> dict:
    return {
        "use_case": "Add IFC upload",
        "refined_use_case": "Add IFC upload with async DIN277 processing",
        "model_used": "claude-opus-test",
        "tier_used": "standard",
        "task_count": 2,
        "total_sub_tasks": 5,
        "total_branches": 3,
        "warnings": [],
        "tasks": [
            {
                "task_id": "T-cad001",
                "title": "Add IFC upload model",
                "type": "feature",
                "complexity": "complex",
                "risk_level": "medium",
                "affected_paths": ["apps/ifc/models.py"],
                "acceptance_criteria": ["IFC parses without error"],
                "graph_id": "TG-cad001",
                "branches": 2,
                "sub_tasks": 3,
                "parallel_groups": [],
                "sub_task_details": [
                    {
                        "id": "ST-1",
                        "title": "Create model",
                        "role": "developer",
                        "gate": "1",
                        "depends_on": [],
                    },
                ],
            }
        ],
    }


def _decompose_payload() -> dict:
    return {
        "use_case": "Add IFC upload",
        "refined_use_case": "Add IFC upload",
        "model_used": "gpt-4o-mini",
        "tier_used": "budget",
        "tasks": [
            {
                "task_id": "T-cad001",
                "title": "Add IFC upload model",
                "type": "feature",
                "complexity": "complex",
                "risk_level": "medium",
                "affected_paths": ["apps/ifc/models.py"],
                "acceptance_criteria": ["IFC parses without error"],
                "context": "IFC processing context",
            }
        ],
        "warnings": [],
    }


# ── Stub Fallback ─────────────────────────────────────────────────────────────


class TestStubFallback:
    def _make_service(self) -> UseCasePipelineService:
        with patch.object(UseCasePipelineService, "_check_direct", return_value=False):
            return UseCasePipelineService()

    def test_should_stub_on_http_failure(self):
        service = self._make_service()
        with patch.object(service, "_http_call", side_effect=Exception("down")):
            result = service.run_pipeline("Add IFC upload")
        assert result["task_count"] == 1

    def test_stub_success_is_false(self):
        service = self._make_service()
        result = service._stub("Add IFC upload", "test reason")
        assert result["success"] is False

    def test_stub_contains_use_case_in_title(self):
        service = self._make_service()
        result = service._stub("IFC async upload", "error")
        assert "IFC async upload" in result["tasks"][0]["title"]

    def test_stub_ids_are_unique(self):
        service = self._make_service()
        r1 = service._stub("x", "e")
        r2 = service._stub("x", "e")
        assert r1["tasks"][0]["task_id"] != r2["tasks"][0]["task_id"]


# ── HTTP Mode ─────────────────────────────────────────────────────────────────


class TestHttpMode:
    def _make_service(self) -> UseCasePipelineService:
        with patch.object(UseCasePipelineService, "_check_direct", return_value=False):
            return UseCasePipelineService(base_url="http://test-orchestrator:8101")

    def _mock_http_response(self, payload: dict) -> MagicMock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": json.dumps(payload)}]}
        mock_response.raise_for_status = MagicMock()
        return mock_response

    def test_should_call_run_use_case_pipeline(self):
        service = self._make_service()
        mock_resp = self._mock_http_response(_pipeline_payload())

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.post.return_value = mock_resp
            result = service.run_pipeline("Add IFC upload", tier="standard")

        assert result["success"] is True
        assert result["task_count"] == 2

    def test_should_call_decompose_use_case(self):
        service = self._make_service()
        mock_resp = self._mock_http_response(_decompose_payload())

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.post.return_value = mock_resp
            result = service.decompose("Add IFC upload", tier="budget")

        assert result["success"] is True
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["type"] == "feature"

    def test_should_fallback_on_connect_error(self):
        service = self._make_service()
        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.post.side_effect = Exception("refused")
            result = service.run_pipeline("Add IFC upload")

        assert result["success"] is False
        assert result["warnings"]

    def test_should_handle_plain_text_response(self):
        service = self._make_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": [{"text": "pipeline summary text"}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.post.return_value = mock_resp
            result = service.run_pipeline("Add IFC upload")

        assert result["success"] is True
        assert result["tasks"] == []


# ── Direct Mode ───────────────────────────────────────────────────────────────


class TestDirectMode:
    def test_should_use_direct_when_available(self):
        service = UseCasePipelineService.__new__(UseCasePipelineService)
        service.base_url = "http://localhost:8101"
        service.timeout = 60.0
        service._direct_available = True

        expected = {"success": True, **_pipeline_payload()}

        with patch.object(service, "_direct_run_pipeline", return_value=expected) as mock_d:
            result = service.run_pipeline(
                "Add IFC upload", context="cad-hub stack", tier="standard"
            )

        mock_d.assert_called_once_with("Add IFC upload", "cad-hub stack", "standard")
        assert result["task_count"] == 2

    def test_direct_decompose_delegates(self):
        service = UseCasePipelineService.__new__(UseCasePipelineService)
        service.base_url = "http://localhost:8101"
        service.timeout = 60.0
        service._direct_available = True

        expected = {"success": True, **_decompose_payload()}

        with patch.object(service, "_direct_decompose", return_value=expected) as mock_d:
            result = service.decompose("Add IFC upload", tier="budget")

        mock_d.assert_called_once_with("Add IFC upload", "", "budget")
        assert result["tasks"][0]["type"] == "feature"


# ── Health Check ──────────────────────────────────────────────────────────────


class TestHealthCheck:
    def test_direct_mode_always_healthy(self):
        service = UseCasePipelineService.__new__(UseCasePipelineService)
        service._direct_available = True
        assert service.health_check() is True

    def test_http_healthy_on_200(self):
        service = UseCasePipelineService.__new__(UseCasePipelineService)
        service._direct_available = False
        service.base_url = "http://test:8101"
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = mock_resp
            assert service.health_check() is True

    def test_http_unhealthy_on_exception(self):
        service = UseCasePipelineService.__new__(UseCasePipelineService)
        service._direct_available = False
        service.base_url = "http://test:8101"

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.side_effect = Exception("down")
            assert service.health_check() is False


# ── Singleton ─────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_get_pipeline_service_singleton(self):
        import apps.core.services.use_case_pipeline_service as mod

        mod._default_service = None
        s1 = get_pipeline_service()
        s2 = get_pipeline_service()
        assert s1 is s2
        mod._default_service = None
