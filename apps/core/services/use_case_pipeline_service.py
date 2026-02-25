"""
UseCasePipelineService — ADR-085 Integration für cad-hub.

Verbindet cad-hub Issue-Triage und Feature-Planung mit der
UseCasePipeline aus dem Orchestrator MCP (mcp-hub).

Pattern analog zu CADMCPBridge (local/remote modes).

Typische Nutzung in cad-hub:
    service = UseCasePipelineService()

    # IFC-Feature planen
    result = service.run_pipeline(
        use_case="Add IFC upload with async processing and DIN277 area calculation",
        context="Stack: Django, Celery, S3. Apps: ifc/, core/. ADR-085.",
        tier="standard",
    )
    for task in result["tasks"]:
        print(f"[{task['type']}/{task['complexity']}] {task['title']}")

    # Issue-Triage (schnell + günstig)
    result = service.decompose(
        use_case=issue_title + " " + issue_body,
        tier="budget",
    )
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_MCP_URL", "http://127.0.0.1:8101")


class UseCasePipelineService:
    """ADR-085 Pipeline-Integration für cad-hub.

    Nutzungsmodi (auto-detect):
        direct:  orchestrator_mcp im PYTHONPATH → In-Process
        http:    ORCHESTRATOR_MCP_URL → HTTP-Gateway
        stub:    Fallback (kein Ausfall, 1 generischer Task)
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or _ORCHESTRATOR_URL).rstrip("/")
        self.timeout = timeout
        self._direct_available = self._check_direct()

    def _check_direct(self) -> bool:
        try:
            from orchestrator_mcp.agent_team.use_case_pipeline import UseCasePipeline  # noqa: F401
            return True
        except ImportError:
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    def run_pipeline(
        self,
        use_case: str,
        context: str = "",
        tier: str = "standard",
    ) -> dict[str, Any]:
        """Use Case → Tasks + TaskGraphs (vollständige Pipeline).

        Empfehlung cad-hub:
            Feature-Planung  → tier="standard"
            Architektur-ADRs → tier="premium"

        Args:
            use_case: Natürlichsprachige Beschreibung
            context:  Stack, ADRs, betroffene Apps (optional)
            tier:     "premium" | "standard" | "budget"

        Returns:
            dict mit success, task_count, total_sub_tasks,
                  summary, tasks (inkl. branches/sub_task_details),
                  warnings
        """
        if self._direct_available:
            return self._direct_run_pipeline(use_case, context, tier)
        return self._http_call("run_use_case_pipeline", {
            "use_case": use_case,
            "context": context,
            "tier": tier,
            "output_format": "json",
        })

    def decompose(
        self,
        use_case: str,
        context: str = "",
        tier: str = "budget",
    ) -> dict[str, Any]:
        """Use Case → strukturierte Tasks (Issue-Triage, kein Planner).

        Empfehlung cad-hub:
            Issue-Triage (hohes Volumen) → tier="budget"
            Gezielte Analysen            → tier="standard"

        Returns:
            dict mit success, tasks, model_used, tier_used, warnings
        """
        if self._direct_available:
            return self._direct_decompose(use_case, context, tier)
        return self._http_call("decompose_use_case", {
            "use_case": use_case,
            "context": context,
            "tier": tier,
            "output_format": "json",
        })

    def health_check(self) -> bool:
        """Prüft ob Orchestrator MCP erreichbar ist."""
        if self._direct_available:
            return True
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{self.base_url}/health")
                return r.status_code == 200
        except Exception:
            return False

    # ── Direct (In-Process) ───────────────────────────────────────────────────

    def _direct_run_pipeline(self, use_case: str, context: str, tier: str) -> dict[str, Any]:
        import asyncio
        try:
            from orchestrator_mcp.agent_team.use_case_pipeline import UseCasePipeline
            pipeline = UseCasePipeline(tier=tier)
            result = asyncio.run(pipeline.run(use_case=use_case, context=context))
            return {"success": True, **result.to_dict()}
        except Exception as exc:
            logger.error("Direct pipeline failed: %s", exc)
            return self._stub(use_case, str(exc))

    def _direct_decompose(self, use_case: str, context: str, tier: str) -> dict[str, Any]:
        import asyncio
        try:
            from orchestrator_mcp.agent_team.use_case_decomposer import UseCaseDecomposer
            decomposer = UseCaseDecomposer(tier=tier)
            result = asyncio.run(decomposer.decompose_async(use_case=use_case, context=context))
            return {
                "success": True,
                "use_case": result.use_case,
                "refined_use_case": result.refined_use_case,
                "model_used": result.model_used,
                "tier_used": result.tier_used,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "title": t.title,
                        "type": t.type.value,
                        "complexity": t.complexity.value,
                        "risk_level": t.risk_level.value,
                        "affected_paths": t.affected_paths,
                        "acceptance_criteria": t.acceptance_criteria,
                        "context": t.context,
                    }
                    for t in result.tasks
                ],
                "warnings": result.warnings,
            }
        except Exception as exc:
            logger.error("Direct decompose failed: %s", exc)
            return self._stub(use_case, str(exc))

    # ── HTTP ──────────────────────────────────────────────────────────────────

    def _http_call(self, tool_name: str, arguments: dict) -> dict[str, Any]:
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/mcp/call",
                    json={"tool": tool_name, "arguments": arguments},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("content", [{}])
                text = content[0].get("text", "{}") if isinstance(content, list) else str(content)
                try:
                    return {"success": True, **json.loads(text)}
                except json.JSONDecodeError:
                    return {"success": True, "summary": text, "tasks": [], "warnings": []}
        except Exception as exc:
            logger.error("HTTP pipeline call to %s failed: %s", self.base_url, exc)
            return self._stub(arguments.get("use_case", ""), str(exc))

    # ── Stub Fallback ─────────────────────────────────────────────────────────

    def _stub(self, use_case: str, reason: str) -> dict[str, Any]:
        return {
            "success": False,
            "use_case": use_case,
            "model_used": "stub",
            "tier_used": "budget",
            "task_count": 1,
            "total_sub_tasks": 1,
            "summary": f"Pipeline nicht verfügbar ({reason})",
            "tasks": [{
                "task_id": f"T-stub-{uuid.uuid4().hex[:6]}",
                "title": f"Implement: {use_case[:80]}",
                "type": "feature",
                "complexity": "moderate",
                "risk_level": "medium",
                "affected_paths": [],
                "acceptance_criteria": ["All tests pass"],
                "context": use_case,
                "graph_id": None,
                "branches": 1,
                "sub_task_details": [],
            }],
            "warnings": [f"Pipeline fallback: {reason}"],
        }


# Singleton
_default_service: UseCasePipelineService | None = None


def get_pipeline_service() -> UseCasePipelineService:
    """Singleton-Accessor für cad-hub Services."""
    global _default_service
    if _default_service is None:
        _default_service = UseCasePipelineService()
    return _default_service
