"""
IssueTriage Service — ADR-085 (cad-hub, standalone).

Kein Django — direkt importierbar im CI-Skript.
"""

from __future__ import annotations

import json as _json
import logging
import os
from dataclasses import dataclass, field
from typing import Any
from urllib import error as _err
from urllib import request as _req

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # hardcoded-ok: standalone CI script
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "achimdehnert/cad-hub")  # hardcoded-ok: standalone CI script

TYPE_LABELS: dict[str, str] = {
    "feature": "type:feature",
    "bugfix": "type:bug",
    "refactor": "type:refactor",
    "test": "type:test",
    "docs": "type:docs",
    "adr": "type:adr",
    "chore": "type:chore",
}

COMPLEXITY_LABELS: dict[str, str] = {
    "trivial": "complexity:trivial",
    "simple": "complexity:simple",
    "moderate": "complexity:moderate",
    "complex": "complexity:complex",
    "architectural": "complexity:architectural",
}

RISK_LABELS: dict[str, str] = {
    "low": "risk:low",
    "medium": "risk:medium",
    "high": "risk:high",
    "critical": "risk:critical",
}

PATH_APP_LABELS: list[tuple[str, str]] = [
    ("apps/ifc", "app:ifc"),
    ("apps/dxf", "app:dxf"),
    ("apps/avb", "app:avb"),
    ("apps/areas", "app:areas"),
    ("apps/brandschutz", "app:brandschutz"),
    ("apps/export", "app:export"),
    ("apps/core", "app:core"),
    ("tests/", "scope:tests"),
    (".github/", "scope:ci"),
    ("config/", "scope:config"),
]

MAX_TASKS_FOR_LABELS = 5


@dataclass
class TriageResult:
    issue_number: int
    title: str
    labels: list[str] = field(default_factory=list)
    tasks_found: int = 0
    model_used: str = "stub"
    tier_used: str = "budget"
    warnings: list[str] = field(default_factory=list)
    github_updated: bool = False
    raw_tasks: list[dict] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if not self.tasks_found:
            return f"Issue #{self.issue_number}: keine Tasks erkannt"
        tl = [l for l in self.labels if l.startswith("type:")]
        cl = [l for l in self.labels if l.startswith("complexity:")]
        al = [l for l in self.labels if l.startswith("app:")]
        parts = []
        if tl:
            parts.append("/".join(t.split(":")[-1] for t in tl))
        if cl:
            parts.append(cl[0].split(":")[-1])
        if al:
            parts.append(", ".join(a.split(":")[-1] for a in al))
        desc = " · ".join(parts) if parts else "keine Labels"
        return (
            f"Issue #{self.issue_number}: {self.tasks_found} Task(s) → "
            f"{len(self.labels)} Labels ({desc})"
        )


class IssueTriageService:
    def __init__(
        self,
        github_token: str | None = None,
        github_repo: str | None = None,
        tier: str = "budget",
        dry_run: bool = False,
    ) -> None:
        self.github_token = github_token or GITHUB_TOKEN
        self.github_repo = github_repo or GITHUB_REPO
        self.tier = tier
        self.dry_run = dry_run

    def triage(
        self,
        issue_number: int,
        title: str,
        body: str = "",
        existing_labels: list[str] | None = None,
    ) -> TriageResult:
        result = TriageResult(issue_number=issue_number, title=title)
        use_case = f"{title}\n\n{body}".strip()
        context = (
            "Repo: cad-hub, Stack: Django/Python, CAD platform, "
            "Apps: ifc, dxf, avb, areas, brandschutz, export, core"
        )

        decomp = self._http_decompose(use_case, context)
        result.warnings.extend(decomp.get("warnings", []))
        result.model_used = decomp.get("model_used", "stub")
        result.tier_used = decomp.get("tier_used", self.tier)
        result.raw_tasks = decomp.get("tasks", [])
        result.tasks_found = len(result.raw_tasks)

        if not result.raw_tasks:
            result.warnings.append("Keine Tasks erkannt — keine Labels gesetzt")
            return result

        result.labels = self._compute_labels(
            result.raw_tasks[:MAX_TASKS_FOR_LABELS],
            existing_labels or [],
        )

        if result.labels and not self.dry_run and self.github_token:
            result.github_updated = self._apply_github_labels(issue_number, result.labels)
        elif self.dry_run:
            logger.info("dry_run: Issue #%d → %s", issue_number, result.labels)

        return result

    def triage_batch(self, issues: list[dict[str, Any]]) -> list[TriageResult]:
        results = []
        for issue in issues:
            try:
                results.append(
                    self.triage(
                        issue_number=issue["number"],
                        title=issue["title"],
                        body=issue.get("body", ""),
                        existing_labels=[l["name"] for l in issue.get("labels", [])],
                    )
                )
            except Exception as exc:
                logger.error("Triage failed for issue #%s: %s", issue.get("number"), exc)
                results.append(
                    TriageResult(
                        issue_number=issue.get("number", 0),
                        title=issue.get("title", ""),
                        warnings=[f"Triage error: {exc}"],
                    )
                )
        return results

    def _http_decompose(self, use_case: str, context: str) -> dict:
        mcp_url = os.environ.get("ORCHESTRATOR_MCP_URL", "http://127.0.0.1:8101")  # hardcoded-ok: standalone CI script
        try:
            payload = _json.dumps(
                {
                    "tool": "decompose_use_case",
                    "arguments": {
                        "use_case": use_case,
                        "context": context,
                        "tier": self.tier,
                        "output_format": "json",
                    },
                }
            ).encode()
            req = _req.Request(
                f"{mcp_url}/mcp/call",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _req.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())
                content = data.get("content", [{}])
                text = content[0].get("text", "{}") if isinstance(content, list) else "{}"
                return {"success": True, **_json.loads(text)}
        except Exception as exc:
            logger.error("HTTP decompose failed: %s", exc)
            return {
                "success": False,
                "tasks": [],
                "warnings": [str(exc)],
                "model_used": "stub",
                "tier_used": self.tier,
            }

    def _compute_labels(self, tasks: list[dict], existing_labels: list[str]) -> list[str]:
        labels: set[str] = set()
        types, complexities, risks, paths = set(), set(), set(), []

        for task in tasks:
            types.add(task.get("type", "feature"))
            complexities.add(task.get("complexity", "moderate"))
            risks.add(task.get("risk_level", "medium"))
            paths.extend(task.get("affected_paths", []))

        for t in types:
            if lbl := TYPE_LABELS.get(t):
                labels.add(lbl)

        co = ["trivial", "simple", "moderate", "complex", "architectural"]
        highest = max(complexities, key=lambda c: co.index(c) if c in co else 0)
        if lbl := COMPLEXITY_LABELS.get(highest):
            labels.add(lbl)

        ro = ["low", "medium", "high", "critical"]
        hr = max(risks, key=lambda r: ro.index(r) if r in ro else 0)
        if hr in ("high", "critical"):
            if lbl := RISK_LABELS.get(hr):
                labels.add(lbl)

        for path in paths:
            for prefix, app_label in PATH_APP_LABELS:
                if path.startswith(prefix) or prefix in path:
                    labels.add(app_label)
                    break

        return sorted(labels - set(existing_labels))

    def _apply_github_labels(self, issue_number: int, labels: list[str]) -> bool:
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues/{issue_number}/labels"
            payload = _json.dumps({"labels": labels}).encode()
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            req = _req.Request(url, data=payload, headers=headers, method="POST")
            with _req.urlopen(req, timeout=15) as resp:
                return resp.status in (200, 201)
        except Exception as exc:
            logger.error("GitHub API Fehler: %s", exc)
            return False
