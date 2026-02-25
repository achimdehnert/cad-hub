#!/usr/bin/env python3
"""
Bootstrap GitHub Labels — ADR-085 Issue Triage.

Erstellt alle Issue-Triage-Labels im GitHub-Repo.
Idempotent — bestehende Labels (HTTP 422) werden übersprungen.
Kein Django/virtualenv nötig — nur stdlib + httpx (oder urllib).

Usage:
    GITHUB_TOKEN=ghp_xxx python bootstrap_labels.py
    GITHUB_TOKEN=ghp_xxx python bootstrap_labels.py --dry-run
    GITHUB_TOKEN=ghp_xxx python bootstrap_labels.py --repo achimdehnert/cad-hub
"""

import argparse
import os
import sys
from urllib import request, error
import json

REPO = os.environ.get("GITHUB_REPOSITORY", "achimdehnert/cad-hub")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ── Label-Definitionen (spiegelt issue_triage_service.py) ─────────────────────

LABELS: list[tuple[str, str, str]] = [
    # (name, hex-color ohne #, description)

    # Type
    ("type:feature",   "0075ca", "New feature or enhancement"),
    ("type:bug",       "d73a4a", "Something is broken"),
    ("type:refactor",  "0075ca", "Code improvement without behavior change"),
    ("type:test",      "0075ca", "Test coverage improvement"),
    ("type:docs",      "0075ca", "Documentation update"),
    ("type:adr",       "0075ca", "Architecture Decision Record"),
    ("type:chore",     "0075ca", "Maintenance / tooling"),

    # Complexity
    ("complexity:trivial",       "e4e669", "< 1h, single line change"),
    ("complexity:simple",        "e4e669", "< 1 day, one component"),
    ("complexity:moderate",      "e4e669", "1–3 days, multiple components"),
    ("complexity:complex",       "e4e669", "3–5 days, cross-app changes"),
    ("complexity:architectural", "e4e669", "> 5 days, system-wide impact"),

    # Risk
    ("risk:high",     "d93f0b", "High risk — careful review needed"),
    ("risk:critical", "b60205", "Critical risk — security/data impact"),

    # App
    ("app:ifc",         "0e8a16", "IFC file handling"),
    ("app:dxf",         "0e8a16", "DXF file handling"),
    ("app:avb",         "0e8a16", "AVB / tender documents"),
    ("app:areas",       "0e8a16", "DIN277 area calculation"),
    ("app:brandschutz", "0e8a16", "Fire protection (Brandschutz)"),
    ("app:export",      "0e8a16", "Export / reporting"),
    ("app:core",        "0e8a16", "Core infrastructure"),

    # Scope
    ("scope:tests",  "c5def5", "Test files affected"),
    ("scope:ci",     "c5def5", "CI/CD pipeline affected"),
    ("scope:config", "c5def5", "Configuration affected"),
]


def create_label(
    session_headers: dict,
    repo: str,
    name: str,
    color: str,
    description: str,
    dry_run: bool,
) -> str:
    """Erstellt ein Label. Gibt 'created', 'exists' oder 'error' zurück."""
    if dry_run:
        return "dry-run"

    url = f"https://api.github.com/repos/{repo}/labels"
    payload = json.dumps({
        "name": name,
        "color": color,
        "description": description,
    }).encode()

    req = request.Request(url, data=payload, headers=session_headers, method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                return "created"
            return f"unexpected:{resp.status}"
    except error.HTTPError as e:
        if e.code == 422:
            return "exists"
        return f"error:{e.code}"
    except Exception as e:
        return f"error:{e}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap GitHub Issue-Triage-Labels (ADR-085)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Keine API-Calls")
    parser.add_argument("--repo", default=REPO, help=f"GitHub Repo (default: {REPO})")
    parser.add_argument("--token", default=TOKEN, help="GitHub Token")
    args = parser.parse_args()

    token = args.token
    repo = args.repo
    dry_run = args.dry_run

    print(f"\n=== Bootstrap GitHub Labels ===")
    print(f"  Repo    : {repo}")
    print(f"  Labels  : {len(LABELS)}")
    print(f"  Dry-run : {dry_run}")
    print()

    if not dry_run and not token:
        print("ERROR: GITHUB_TOKEN nicht gesetzt.")
        print("  Setze env-Variable: export GITHUB_TOKEN=ghp_xxx")
        print("  Oder übergib --token ghp_xxx")
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    created, exists, errors = [], [], []

    for name, color, description in LABELS:
        status = create_label(headers, repo, name, color, description, dry_run)
        if status == "created":
            created.append(name)
            print(f"  + {name}")
        elif status in ("exists", "dry-run"):
            exists.append(name)
            marker = "~" if dry_run else "="
            print(f"  {marker} {name}")
        else:
            errors.append((name, status))
            print(f"  ! {name}  [{status}]", file=sys.stderr)

    print()
    if dry_run:
        print(f"[dry-run] Würde {len(LABELS)} Labels in '{repo}' anlegen.")
    else:
        print(f"Fertig:")
        print(f"  Erstellt  : {len(created)}")
        print(f"  Vorhanden : {len(exists)}")
        print(f"  Fehler    : {len(errors)}")

    if errors:
        print("\nFehler Details:")
        for name, status in errors:
            print(f"  {name}: {status}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
