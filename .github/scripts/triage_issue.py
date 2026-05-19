#!/usr/bin/env python3
"""
Issue Triage Script — ADR-085 (cad-hub).

Standalone — kein Django nötig.
Importiert IssueTriageService direkt aus .github/scripts/issue_triage_service.py.

Usage:
    python .github/scripts/triage_issue.py \
        --issue-number 42 \
        --title "Add IFC upload" \
        --body "Users need to upload IFC files..."
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from issue_triage_service import IssueTriageService


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage a GitHub issue")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--body", type=str, default="")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--tier", type=str, default="budget")
    args = parser.parse_args()
    body = args.body

    service = IssueTriageService(
        github_token=os.environ.get("GITHUB_TOKEN", ""),  # hardcoded-ok: standalone CI script
        github_repo=os.environ.get(
            "GITHUB_REPOSITORY", "achimdehnert/cad-hub"
        ),  # hardcoded-ok: standalone CI script
        tier=args.tier,
        dry_run=args.dry_run,
    )

    print(f"Triage Issue #{args.issue_number}: {args.title[:60]}")
    result = service.triage(
        issue_number=args.issue_number,
        title=args.title,
        body=body or "",
    )

    print(f"  Tasks erkannt : {result.tasks_found}")
    print(f"  Labels        : {result.labels}")
    print(f"  GitHub updated: {result.github_updated}")
    print(f"  Modell        : {result.model_used} / {result.tier_used}")

    if result.warnings:
        for w in result.warnings:
            print(f"  [warn] {w}")

    print(result.summary)
    # Exit 0 auch wenn kein MCP-Server erreichbar — das ist im CI erwartet
    return 0


if __name__ == "__main__":
    sys.exit(main())
