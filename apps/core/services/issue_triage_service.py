"""
IssueTriage Service — ADR-085 automatisches Issue-Labeling für cad-hub.

Ablauf:
    1. GitHub Issue (title + body) → UseCasePipelineService.decompose()
    2. Tasks → Label-Mapping (TaskType, Complexity, Risk, affected_paths)
    3. Labels via GitHub API setzen

Tier: "budget" (hohes Issue-Volumen, einfache Strukturierung reicht)

Usage:
    service = IssueTriageService()
    result = service.triage(
        issue_number=42,
        title="Add IFC upload with async processing",
        body="Users need to upload IFC files...",
    )
    print(result.labels)   # ["type:feature", "complexity:complex", "app:ifc"]
    print(result.summary)  # Kurze Beschreibung was erkannt wurde
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "achimdehnert/cad-hub")


# ── Label-Definitionen ────────────────────────────────────────────────────────

# TaskType → GitHub Label
TYPE_LABELS: dict[str, str] = {
    "feature":   "type:feature",
    "bugfix":    "type:bug",
    "refactor":  "type:refactor",
    "test":      "type:test",
    "docs":      "type:docs",
    "adr":       "type:adr",
    "chore":     "type:chore",
}

# Complexity → GitHub Label
COMPLEXITY_LABELS: dict[str, str] = {
    "trivial":       "complexity:trivial",
    "simple":        "complexity:simple",
    "moderate":      "complexity:moderate",
    "complex":       "complexity:complex",
    "architectural": "complexity:architectural",
}

# Risk → GitHub Label
RISK_LABELS: dict[str, str] = {
    "low":      "risk:low",
    "medium":   "risk:medium",
    "high":     "risk:high",
    "critical": "risk:critical",
}

# affected_paths → App-Label (Präfix-Matching)
PATH_APP_LABELS: list[tuple[str, str]] = [
    ("apps/ifc",         "app:ifc"),
    ("apps/dxf",         "app:dxf"),
    ("apps/avb",         "app:avb"),
    ("apps/areas",       "app:areas"),
    ("apps/brandschutz", "app:brandschutz"),
    ("apps/export",      "app:export"),
    ("apps/core",        "app:core"),
    ("tests/",           "scope:tests"),
    (".github/",         "scope:ci"),
    ("config/",          "scope:config"),
]

# Maximale Anzahl Tasks für Budget-Tier (kostenoptimiert)
MAX_TASKS_FOR_LABELS = 5


# ── Ergebnis ──────────────────────────────────────────────────────────────────

@dataclass
class TriageResult:
    """Ergebnis einer Issue-Triage-Ausführung."""

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
        type_labels = [l for l in self.labels if l.startswith("type:")]
        complexity_labels = [l for l in self.labels if l.startswith("complexity:")]
        app_labels = [l for l in self.labels if l.startswith("app:")]
        parts = []
        if type_labels:
            parts.append("/".join(t.split(":")[-1] for t in type_labels))
        if complexity_labels:
            parts.append(complexity_labels[0].split(":")[-1])
        if app_labels:
            parts.append(", ".join(a.split(":")[-1] for a in app_labels))
        desc = " · ".join(parts) if parts else "keine Labels"
        return (
            f"Issue #{self.issue_number}: {self.tasks_found} Task(s) → "
            f"{len(self.labels)} Labels ({desc})"
        )


# ── Service ───────────────────────────────────────────────────────────────────

class IssueTriageService:
    """Automatisches Issue-Labeling via UseCasePipeline (ADR-085).

    Nutzung:
        service = IssueTriageService()
        result = service.triage(42, "Add IFC upload", "...")
        # result.labels → ["type:feature", "complexity:complex", "app:ifc"]
        # result.github_updated → True wenn Labels via API gesetzt
    """

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

        from apps.core.services.use_case_pipeline_service import UseCasePipelineService
        self._pipeline = UseCasePipelineService()

    def triage(
        self,
        issue_number: int,
        title: str,
        body: str = "",
        existing_labels: list[str] | None = None,
    ) -> TriageResult:
        """Issue triagen: decompose + labels berechnen + GitHub updaten.

        Args:
            issue_number:    GitHub Issue Nummer
            title:           Issue-Titel
            body:            Issue-Body (Markdown)
            existing_labels: Bereits gesetzte Labels (werden nicht überschrieben)

        Returns:
            TriageResult mit berechneten Labels + github_updated Status
        """
        result = TriageResult(issue_number=issue_number, title=title)

        # 1. Decomposition
        use_case = f"{title}\n\n{body}".strip()
        context = (
            f"Repo: cad-hub, Stack: Django/Python, "
            f"Apps: ifc, dxf, avb, areas, brandschutz, export, core"
        )
        decomp = self._pipeline.decompose(
            use_case=use_case,
            context=context,
            tier=self.tier,
        )
        result.warnings.extend(decomp.get("warnings", []))
        result.model_used = decomp.get("model_used", "stub")
        result.tier_used = decomp.get("tier_used", self.tier)
        result.raw_tasks = decomp.get("tasks", [])
        result.tasks_found = len(result.raw_tasks)

        if not result.raw_tasks:
            result.warnings.append("Keine Tasks erkannt — keine Labels gesetzt")
            return result

        # 2. Labels berechnen
        new_labels = self._compute_labels(
            result.raw_tasks[:MAX_TASKS_FOR_LABELS],
            existing_labels or [],
        )
        result.labels = new_labels

        # 3. GitHub Labels setzen
        if new_labels and not self.dry_run and self.github_token:
            result.github_updated = self._apply_github_labels(
                issue_number, new_labels
            )
        elif self.dry_run:
            logger.info(
                "dry_run: Issue #%d würde Labels erhalten: %s",
                issue_number, new_labels,
            )

        return result

    def triage_batch(
        self,
        issues: list[dict[str, Any]],
    ) -> list[TriageResult]:
        """Mehrere Issues auf einmal triagen.

        Args:
            issues: Liste von dicts mit keys: number, title, body, labels
        """
        results = []
        for issue in issues:
            try:
                result = self.triage(
                    issue_number=issue["number"],
                    title=issue["title"],
                    body=issue.get("body", ""),
                    existing_labels=[l["name"] for l in issue.get("labels", [])],
                )
                results.append(result)
            except Exception as exc:
                logger.error("Triage failed for issue #%s: %s", issue.get("number"), exc)
                results.append(TriageResult(
                    issue_number=issue.get("number", 0),
                    title=issue.get("title", ""),
                    warnings=[f"Triage error: {exc}"],
                ))
        return results

    # ── Label-Berechnung ──────────────────────────────────────────────────────

    def _compute_labels(
        self,
        tasks: list[dict],
        existing_labels: list[str],
    ) -> list[str]:
        """Berechnet GitHub-Labels aus Task-Liste."""
        labels: set[str] = set()

        # Sammle einmalige Werte über alle Tasks
        types: set[str] = set()
        complexities: set[str] = set()
        risks: set[str] = set()
        paths: list[str] = []

        for task in tasks:
            types.add(task.get("type", "feature"))
            complexities.add(task.get("complexity", "moderate"))
            risks.add(task.get("risk_level", "medium"))
            paths.extend(task.get("affected_paths", []))

        # Type-Labels (alle erkannten Typen)
        for t in types:
            if label := TYPE_LABELS.get(t):
                labels.add(label)

        # Complexity: höchste Komplexität gewinnt
        complexity_order = ["trivial", "simple", "moderate", "complex", "architectural"]
        highest = max(complexities, key=lambda c: complexity_order.index(c)
                      if c in complexity_order else 0)
        if label := COMPLEXITY_LABELS.get(highest):
            labels.add(label)

        # Risk: höchstes Risk gewinnt
        risk_order = ["low", "medium", "high", "critical"]
        highest_risk = max(risks, key=lambda r: risk_order.index(r)
                           if r in risk_order else 0)
        if highest_risk in ("high", "critical"):
            if label := RISK_LABELS.get(highest_risk):
                labels.add(label)

        # App-Labels aus affected_paths
        for path in paths:
            for prefix, app_label in PATH_APP_LABELS:
                if path.startswith(prefix) or prefix in path:
                    labels.add(app_label)
                    break

        # Keine bestehenden Labels überschreiben
        existing_set = set(existing_labels)
        new_labels = sorted(labels - existing_set)

        logger.debug(
            "Computed %d new labels for issue (from %d tasks): %s",
            len(new_labels), len(tasks), new_labels,
        )
        return new_labels

    # ── GitHub API ────────────────────────────────────────────────────────────

    def _apply_github_labels(
        self,
        issue_number: int,
        labels: list[str],
    ) -> bool:
        """Setzt Labels via GitHub REST API."""
        try:
            import httpx
            url = f"https://api.github.com/repos/{self.github_repo}/issues/{issue_number}/labels"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            with httpx.Client(timeout=15.0) as client:
                # Labels hinzufügen (POST = additive, überschreibt nicht)
                response = client.post(url, json={"labels": labels}, headers=headers)
                if response.status_code in (200, 201):
                    logger.info(
                        "GitHub Labels gesetzt für Issue #%d: %s",
                        issue_number, labels,
                    )
                    return True
                logger.error(
                    "GitHub Labels fehlgeschlagen für Issue #%d: %s %s",
                    issue_number, response.status_code, response.text[:200],
                )
                return False
        except ImportError:
            logger.warning("httpx nicht installiert — GitHub Labels nicht gesetzt")
            return False
        except Exception as exc:
            logger.error("GitHub API Fehler: %s", exc)
            return False

    def ensure_labels_exist(self) -> list[str]:
        """Stellt sicher dass alle Label-Definitionen im Repo existieren.

        Idempotent — bestehende Labels werden nicht überschrieben.
        Gibt Liste der neu erstellten Labels zurück.
        """
        all_labels = (
            list(TYPE_LABELS.values())
            + list(COMPLEXITY_LABELS.values())
            + list(RISK_LABELS.values())
            + [l for _, l in PATH_APP_LABELS]
        )
        label_colors = {
            "type:":       "0075ca",
            "complexity:": "e4e669",
            "risk:":       "d93f0b",
            "app:":        "0e8a16",
            "scope:":      "c5def5",
        }
        created = []
        try:
            import httpx
            url = f"https://api.github.com/repos/{self.github_repo}/labels"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            with httpx.Client(timeout=15.0) as client:
                for label_name in all_labels:
                    color = next(
                        (c for prefix, c in label_colors.items()
                         if label_name.startswith(prefix)),
                        "ededed",
                    )
                    response = client.post(
                        url,
                        json={"name": label_name, "color": color},
                        headers=headers,
                    )
                    if response.status_code == 201:
                        created.append(label_name)
                    # 422 = bereits vorhanden → ok
        except Exception as exc:
            logger.error("ensure_labels_exist failed: %s", exc)
        return created


# ── Singleton ─────────────────────────────────────────────────────────────────

_default_triage: IssueTriageService | None = None


def get_triage_service(dry_run: bool = False) -> IssueTriageService:
    """Singleton-Accessor."""
    global _default_triage
    if _default_triage is None or _default_triage.dry_run != dry_run:
        _default_triage = IssueTriageService(dry_run=dry_run)
    return _default_triage
