#!/usr/bin/env python3
"""
Issue Triage Script — ADR-085.

Wird von GitHub Actions aufgerufen wenn ein Issue geöffnet/editiert wird.
Ruft IssueTriageService auf und setzt Labels via GitHub API.

Usage:
    python .github/scripts/triage_issue.py \
        --issue-number 42 \
        --title "Add IFC upload" \
        --body "Users need to upload IFC files..."
"""

import argparse
import json
import os
import sys

# Projektroot zum PYTHONPATH hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from apps.core.services.issue_triage_service import IssueTriageService


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage a GitHub issue")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--body", type=str, default="")
    parser.add_argument("--body-file", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--tier", type=str, default="budget")
    args = parser.parse_args()

    body = args.body
    if args.body_file:
        try:
            with open(args.body_file) as f:
                raw = f.read().strip()
            # GitHub Actions übergibt body als JSON-String via toJSON()
            body = json.loads(raw) if raw.startswith('"') else raw
        except Exception as e:
            print(f"[warn] body-file lesen fehlgeschlagen: {e}")

    service = IssueTriageService(
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        github_repo=os.environ.get("GITHUB_REPOSITORY", "achimdehnert/cad-hub"),
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
    return 0 if result.tasks_found > 0 or not result.warnings else 1


if __name__ == "__main__":
    sys.exit(main())
