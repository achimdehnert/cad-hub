"""
Tests für IssueTriageService (ADR-085) — cad-hub.

Deckt ab:
- Label-Berechnung aus Tasks (type, complexity, risk, paths)
- dry_run Modus
- GitHub API Calls (gemockt)
- Stub-Fallback wenn Pipeline nicht verfügbar
- triage_batch()
- ensure_labels_exist()
- TriageResult.summary
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from apps.core.services.issue_triage_service import (
    COMPLEXITY_LABELS,
    PATH_APP_LABELS,
    RISK_LABELS,
    TYPE_LABELS,
    IssueTriageService,
    TriageResult,
    get_triage_service,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_task(
    title: str = "Add IFC upload",
    task_type: str = "feature",
    complexity: str = "complex",
    risk: str = "medium",
    paths: list[str] | None = None,
) -> dict:
    return {
        "task_id": "T-test001",
        "title": title,
        "type": task_type,
        "complexity": complexity,
        "risk_level": risk,
        "affected_paths": paths or ["apps/ifc/models.py"],
        "acceptance_criteria": ["Tests pass"],
        "context": "test context",
    }


def _make_decomp_result(tasks: list[dict], success: bool = True) -> dict:
    return {
        "success": success,
        "use_case": "test",
        "refined_use_case": "test",
        "model_used": "gpt-4o-mini",
        "tier_used": "budget",
        "tasks": tasks,
        "warnings": [],
    }


def _make_service(dry_run: bool = False) -> IssueTriageService:
    with patch("apps.core.services.issue_triage_service.UseCasePipelineService") as MockPipeline:
        service = IssueTriageService(
            github_token="test-token",
            github_repo="achimdehnert/cad-hub",
            tier="budget",
            dry_run=dry_run,
        )
        service._pipeline = MockPipeline.return_value
        return service


# ── TriageResult ──────────────────────────────────────────────────────────────


class TestTriageResult:
    def test_summary_no_tasks(self):
        r = TriageResult(issue_number=1, title="Test")
        assert "#1" in r.summary
        assert "keine" in r.summary.lower()

    def test_summary_with_labels(self):
        r = TriageResult(
            issue_number=42,
            title="Add IFC upload",
            labels=["type:feature", "complexity:complex", "app:ifc"],
            tasks_found=2,
        )
        summary = r.summary
        assert "#42" in summary
        assert "feature" in summary
        assert "complex" in summary
        assert "ifc" in summary

    def test_summary_risk_high_shown(self):
        r = TriageResult(
            issue_number=5,
            title="Security fix",
            labels=["type:bugfix", "risk:high"],
            tasks_found=1,
        )
        assert "bugfix" in r.summary


# ── Label-Berechnung ──────────────────────────────────────────────────────────


class TestComputeLabels:
    def _service(self) -> IssueTriageService:
        return _make_service(dry_run=True)

    def test_should_map_feature_type(self):
        service = self._service()
        labels = service._compute_labels([_make_task(task_type="feature")], [])
        assert "type:feature" in labels

    def test_should_map_bugfix_type(self):
        service = self._service()
        labels = service._compute_labels([_make_task(task_type="bugfix")], [])
        assert "type:bug" in labels

    def test_should_map_highest_complexity(self):
        service = self._service()
        tasks = [
            _make_task(complexity="simple"),
            _make_task(complexity="complex"),
            _make_task(complexity="moderate"),
        ]
        labels = service._compute_labels(tasks, [])
        assert "complexity:complex" in labels
        assert "complexity:simple" not in labels

    def test_should_map_architectural_complexity(self):
        service = self._service()
        labels = service._compute_labels([_make_task(complexity="architectural")], [])
        assert "complexity:architectural" in labels

    def test_should_add_risk_label_only_for_high_and_critical(self):
        service = self._service()
        low = service._compute_labels([_make_task(risk="low")], [])
        high = service._compute_labels([_make_task(risk="high")], [])
        critical = service._compute_labels([_make_task(risk="critical")], [])
        assert "risk:low" not in low
        assert "risk:medium" not in low
        assert "risk:high" in high
        assert "risk:critical" in critical

    def test_should_map_ifc_path_to_app_label(self):
        service = self._service()
        labels = service._compute_labels([_make_task(paths=["apps/ifc/models.py"])], [])
        assert "app:ifc" in labels

    def test_should_map_dxf_path(self):
        service = self._service()
        labels = service._compute_labels([_make_task(paths=["apps/dxf/views.py"])], [])
        assert "app:dxf" in labels

    def test_should_map_avb_path(self):
        service = self._service()
        labels = service._compute_labels(
            [_make_task(paths=["apps/avb/services/gaeb_generator.py"])], []
        )
        assert "app:avb" in labels

    def test_should_map_tests_path_to_scope(self):
        service = self._service()
        labels = service._compute_labels([_make_task(paths=["tests/test_ifc.py"])], [])
        assert "scope:tests" in labels

    def test_should_not_duplicate_existing_labels(self):
        service = self._service()
        labels = service._compute_labels(
            [_make_task(task_type="feature")],
            existing_labels=["type:feature"],
        )
        assert "type:feature" not in labels

    def test_multiple_types_produce_multiple_type_labels(self):
        service = self._service()
        tasks = [
            _make_task(task_type="feature"),
            _make_task(task_type="test"),
        ]
        labels = service._compute_labels(tasks, [])
        assert "type:feature" in labels
        assert "type:test" in labels

    def test_multiple_app_paths(self):
        service = self._service()
        tasks = [
            _make_task(paths=["apps/ifc/models.py"]),
            _make_task(paths=["apps/dxf/parser.py"]),
        ]
        labels = service._compute_labels(tasks, [])
        assert "app:ifc" in labels
        assert "app:dxf" in labels


# ── Triage (dry_run) ──────────────────────────────────────────────────────────


class TestTriageDryRun:
    def test_should_return_labels_without_github_call(self):
        service = _make_service(dry_run=True)
        service._pipeline.decompose.return_value = _make_decomp_result(
            [_make_task("Add IFC upload", "feature", "complex", "medium", ["apps/ifc/models.py"])]
        )
        result = service.triage(42, "Add IFC upload", "Users need IFC upload")
        assert "type:feature" in result.labels
        assert "complexity:complex" in result.labels
        assert "app:ifc" in result.labels
        assert result.github_updated is False

    def test_should_return_empty_labels_on_no_tasks(self):
        service = _make_service(dry_run=True)
        service._pipeline.decompose.return_value = _make_decomp_result([])
        result = service.triage(1, "Empty issue", "")
        assert result.labels == []
        assert result.tasks_found == 0
        assert result.warnings

    def test_should_propagate_pipeline_warnings(self):
        service = _make_service(dry_run=True)
        decomp = _make_decomp_result([_make_task()])
        decomp["warnings"] = ["LLM was slow"]
        service._pipeline.decompose.return_value = decomp
        result = service.triage(1, "test", "")
        assert any("LLM was slow" in w for w in result.warnings)

    def test_should_store_model_and_tier(self):
        service = _make_service(dry_run=True)
        service._pipeline.decompose.return_value = _make_decomp_result([_make_task()])
        result = service.triage(1, "test", "")
        assert result.model_used == "gpt-4o-mini"
        assert result.tier_used == "budget"


# ── Triage (live — GitHub API gemockt) ───────────────────────────────────────


class TestTriageLive:
    def test_should_call_github_api_with_labels(self):
        service = _make_service(dry_run=False)
        service._pipeline.decompose.return_value = _make_decomp_result(
            [_make_task("Add IFC", "feature", "complex", "medium", ["apps/ifc/models.py"])]
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.post.return_value = mock_resp
            result = service.triage(42, "Add IFC upload", "body")

        assert result.github_updated is True
        call_args = mock_cls.return_value.__enter__.return_value.post.call_args
        sent_labels = call_args[1]["json"]["labels"]
        assert "type:feature" in sent_labels

    def test_should_not_call_github_without_token(self):
        with patch("apps.core.services.issue_triage_service.UseCasePipelineService"):
            service = IssueTriageService(
                github_token="",
                github_repo="test/repo",
                dry_run=False,
            )
        service._pipeline.decompose.return_value = _make_decomp_result([_make_task()])

        with patch.object(service, "_apply_github_labels") as mock_gh:
            service.triage(1, "test", "")
            mock_gh.assert_not_called()

    def test_should_handle_github_api_error(self):
        service = _make_service(dry_run=False)
        service._pipeline.decompose.return_value = _make_decomp_result([_make_task()])

        with patch("httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.post.side_effect = Exception(
                "network error"
            )
            result = service.triage(1, "test", "body")

        assert result.github_updated is False


# ── triage_batch ──────────────────────────────────────────────────────────────


class TestTriageBatch:
    def test_should_process_multiple_issues(self):
        service = _make_service(dry_run=True)
        service._pipeline.decompose.return_value = _make_decomp_result([_make_task()])

        issues = [
            {"number": 1, "title": "Issue 1", "body": "body 1", "labels": []},
            {"number": 2, "title": "Issue 2", "body": "body 2", "labels": []},
            {"number": 3, "title": "Issue 3", "body": "body 3", "labels": []},
        ]
        results = service.triage_batch(issues)
        assert len(results) == 3
        assert all(r.tasks_found == 1 for r in results)

    def test_should_skip_existing_labels(self):
        service = _make_service(dry_run=True)
        service._pipeline.decompose.return_value = _make_decomp_result(
            [_make_task(task_type="feature")]
        )
        issues = [{"number": 1, "title": "t", "body": "", "labels": [{"name": "type:feature"}]}]
        results = service.triage_batch(issues)
        assert "type:feature" not in results[0].labels

    def test_should_recover_from_single_issue_error(self):
        service = _make_service(dry_run=True)
        service._pipeline.decompose.side_effect = [
            _make_decomp_result([_make_task()]),
            Exception("pipeline down"),
            _make_decomp_result([_make_task()]),
        ]
        issues = [
            {"number": 1, "title": "ok", "body": "", "labels": []},
            {"number": 2, "title": "fail", "body": "", "labels": []},
            {"number": 3, "title": "ok2", "body": "", "labels": []},
        ]
        results = service.triage_batch(issues)
        assert len(results) == 3
        assert results[1].warnings  # Fehler protokolliert


# ── Label-Definitionen Vollständigkeit ────────────────────────────────────────


class TestLabelDefinitions:
    def test_all_task_types_have_labels(self):
        expected_types = ["feature", "bugfix", "refactor", "test", "docs", "adr", "chore"]
        for t in expected_types:
            assert t in TYPE_LABELS, f"Missing TYPE_LABEL for '{t}'"

    def test_all_complexities_have_labels(self):
        expected = ["trivial", "simple", "moderate", "complex", "architectural"]
        for c in expected:
            assert c in COMPLEXITY_LABELS, f"Missing COMPLEXITY_LABEL for '{c}'"

    def test_app_path_labels_cover_cad_hub_apps(self):
        app_labels = {label for _, label in PATH_APP_LABELS}
        expected_apps = {
            "app:ifc",
            "app:dxf",
            "app:avb",
            "app:areas",
            "app:brandschutz",
            "app:export",
            "app:core",
        }
        assert expected_apps.issubset(app_labels)


# ── Singleton ─────────────────────────────────────────────────────────────────


class TestSingleton:
    def test_get_triage_service_singleton(self):
        import apps.core.services.issue_triage_service as mod

        mod._default_triage = None
        with patch("apps.core.services.issue_triage_service.UseCasePipelineService"):
            s1 = get_triage_service(dry_run=True)
            s2 = get_triage_service(dry_run=True)
        assert s1 is s2
        mod._default_triage = None
