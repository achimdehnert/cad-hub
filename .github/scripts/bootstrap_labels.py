#!/usr/bin/env python3
"""
bootstrap_labels.py — Idempotentes GitHub Label Setup für 137-hub.

Usage:
    python .github/scripts/bootstrap_labels.py --repo achimdehnert/137-hub --token $GITHUB_TOKEN

Requires: requests
    pip install requests
"""

import argparse
import sys

import requests

LABELS = [
    # ── Type ─────────────────────────────────────────────────────────────────
    {"name": "bug",              "color": "d73a4a", "description": "Fehler / unerwartetes Verhalten"},
    {"name": "enhancement",      "color": "a2eeef", "description": "Neue Funktion oder Verbesserung"},
    {"name": "task",             "color": "e4e669", "description": "Technische Aufgabe / Chore"},
    {"name": "use-case",         "color": "0075ca", "description": "Use Case Definition"},
    {"name": "adr",              "color": "7057ff", "description": "Architecture Decision Record"},
    {"name": "hotfix",           "color": "b60205", "description": "Kritischer Produktions-Fix"},
    {"name": "tech-debt",        "color": "f9d0c4", "description": "Technische Schuld"},
    {"name": "ci-cd",            "color": "1d76db", "description": "CI/CD Pipeline & Deployment"},
    # ── Severity (used by bug_report.yml + triage workflow) ──────────────────
    {"name": "severity:critical", "color": "b60205", "description": "System down / Datenverlust"},
    {"name": "severity:high",     "color": "e4e669", "description": "Major Feature kaputt"},
    {"name": "severity:medium",   "color": "fbca04", "description": "Feature teilweise kaputt"},
    {"name": "severity:low",      "color": "c2e0c6", "description": "Kleineres Problem / kosmetisch"},
    # ── Status ───────────────────────────────────────────────────────────────
    {"name": "triage",           "color": "e99695", "description": "Neu, noch nicht bewertet"},
    {"name": "blocked",          "color": "ee0701", "description": "Warten auf externe Dependency"},
    {"name": "wontfix",          "color": "ffffff", "description": "Bewusst nicht umgesetzt"},
    # ── Meta ─────────────────────────────────────────────────────────────────
    {"name": "good first issue", "color": "7fc97f", "description": "Geeignet für Einsteiger"},
    {"name": "documentation",    "color": "0075ca", "description": "Nur Dokumentation"},
    {"name": "security",         "color": "ee0701", "description": "Sicherheitsrelevant"},
    {"name": "performance",      "color": "fbca04", "description": "Performance-Optimierung"},
    {"name": "dependencies",     "color": "0366d6", "description": "Dependency Update"},
]


def get_existing_labels(session: requests.Session, repo: str) -> dict[str, dict]:
    url = f"https://api.github.com/repos/{repo}/labels"
    params = {"per_page": 100}
    existing = {}
    while url:
        resp = session.get(url, params=params)
        resp.raise_for_status()
        for label in resp.json():
            existing[label["name"]] = label
        url = resp.links.get("next", {}).get("url")
        params = {}
    return existing


def upsert_label(session: requests.Session, repo: str, label: dict, existing: dict) -> str:
    name = label["name"]
    if name in existing:
        url = f"https://api.github.com/repos/{repo}/labels/{requests.utils.quote(name)}"
        resp = session.patch(url, json=label)
        resp.raise_for_status()
        return "updated"
    else:
        url = f"https://api.github.com/repos/{repo}/labels"
        resp = session.post(url, json=label)
        resp.raise_for_status()
        return "created"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap GitHub labels idempotently.")
    parser.add_argument("--repo", required=True, help="owner/repo (e.g. achimdehnert/137-hub)")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {args.token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    print(f"Fetching existing labels for {args.repo} ...")
    existing = get_existing_labels(session, args.repo)
    print(f"  Found {len(existing)} existing labels.")

    for label in LABELS:
        action = upsert_label(session, args.repo, label, existing)
        symbol = "✓" if action == "created" else "↻"
        print(f"  {symbol} [{action}] {label['name']}")

    print(f"\nDone. {len(LABELS)} labels bootstrapped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
