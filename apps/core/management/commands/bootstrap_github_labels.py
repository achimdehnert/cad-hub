"""
Management Command: bootstrap_github_labels

Erstellt alle Issue-Triage-Labels (ADR-085) im GitHub-Repo.
Idempotent — bestehende Labels werden nicht überschrieben.

Usage:
    # Vorschau (kein API-Call)
    python manage.py bootstrap_github_labels --dry-run

    # Ausführen
    GITHUB_TOKEN=ghp_xxx python manage.py bootstrap_github_labels

    # Anderes Repo
    python manage.py bootstrap_github_labels --repo achimdehnert/cad-hub

Exit codes:
    0 — Erfolg (auch wenn keine neuen Labels erstellt wurden)
    1 — GitHub API nicht erreichbar / Token fehlt
"""

import os

from django.core.management.base import BaseCommand, CommandError

from apps.core.services.issue_triage_service import (
    COMPLEXITY_LABELS,
    PATH_APP_LABELS,
    RISK_LABELS,
    TYPE_LABELS,
    IssueTriageService,
)

LABEL_COLORS = {
    "type:":       ("0075ca", "Issue Type"),
    "complexity:": ("e4e669", "Task Complexity"),
    "risk:":       ("d93f0b", "Risk Level"),
    "app:":        ("0e8a16", "Affected App"),
    "scope:":      ("c5def5", "Scope"),
}

ALL_LABELS = (
    list(TYPE_LABELS.values())
    + list(COMPLEXITY_LABELS.values())
    + list(RISK_LABELS.values())
    + [label for _, label in PATH_APP_LABELS]
)


class Command(BaseCommand):
    help = "Bootstrap GitHub Issue-Triage-Labels für cad-hub (ADR-085). Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Labels anzeigen ohne GitHub API aufzurufen",
        )
        parser.add_argument(
            "--repo",
            type=str,
            default=os.environ.get("GITHUB_REPOSITORY", "achimdehnert/cad-hub"),
            help="GitHub Repo (default: GITHUB_REPOSITORY env oder achimdehnert/cad-hub)",
        )
        parser.add_argument(
            "--token",
            type=str,
            default=os.environ.get("GITHUB_TOKEN", ""),
            help="GitHub Token (default: GITHUB_TOKEN env)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        repo = options["repo"]
        token = options["token"]

        self.stdout.write(self.style.HTTP_INFO(
            f"\n=== Bootstrap GitHub Labels — {repo} ==="
        ))
        self.stdout.write(f"  Labels gesamt : {len(ALL_LABELS)}")
        self.stdout.write(f"  Dry-run       : {dry_run}")
        self.stdout.write("")

        # Label-Übersicht ausgeben
        groups = {
            "Type Labels":       list(TYPE_LABELS.values()),
            "Complexity Labels": list(COMPLEXITY_LABELS.values()),
            "Risk Labels":       list(RISK_LABELS.values()),
            "App Labels":        [l for _, l in PATH_APP_LABELS],
        }
        for group, labels in groups.items():
            self.stdout.write(self.style.MIGRATE_HEADING(f"  {group}:"))
            for label in labels:
                color = self._get_color(label)
                self.stdout.write(f"    #{color}  {label}")

        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {len(ALL_LABELS)} Labels würden im Repo '{repo}' erstellt."
            ))
            self.stdout.write(
                "  Ausführen ohne --dry-run um Labels tatsächlich zu erstellen."
            )
            return

        if not token:
            raise CommandError(
                "GITHUB_TOKEN nicht gesetzt. "
                "Setze env-Variable oder übergib --token ghp_xxx"
            )

        # API aufrufen via IssueTriageService
        service = IssueTriageService(
            github_token=token,
            github_repo=repo,
            dry_run=False,
        )

        self.stdout.write("Erstelle Labels via GitHub API...")
        created = self._create_labels(token, repo)

        if created:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ {len(created)} neue Labels erstellt:"
            ))
            for label in created:
                self.stdout.write(f"  + {label}")
        else:
            self.stdout.write(self.style.SUCCESS(
                "\n✓ Alle Labels bereits vorhanden — nichts zu tun."
            ))

        skipped = len(ALL_LABELS) - len(created)
        self.stdout.write(f"\n  Erstellt : {len(created)}")
        self.stdout.write(f"  Vorhanden: {skipped}")
        self.stdout.write(f"  Gesamt   : {len(ALL_LABELS)}")

    def _create_labels(self, token: str, repo: str) -> list[str]:
        """Erstellt Labels via GitHub REST API. Gibt neue Labels zurück."""
        try:
            import httpx
        except ImportError:
            raise CommandError("httpx nicht installiert: pip install httpx")

        url = f"https://api.github.com/repos/{repo}/labels"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        created = []

        with httpx.Client(timeout=15.0) as client:
            for label_name in ALL_LABELS:
                color = self._get_color(label_name)
                description = self._get_description(label_name)

                response = client.post(
                    url,
                    json={
                        "name": label_name,
                        "color": color,
                        "description": description,
                    },
                    headers=headers,
                )

                if response.status_code == 201:
                    created.append(label_name)
                    self.stdout.write(f"  + {label_name}")
                elif response.status_code == 422:
                    # Already exists
                    self.stdout.write(f"  = {label_name} (vorhanden)")
                else:
                    self.stderr.write(
                        f"  ! {label_name} → HTTP {response.status_code}: "
                        f"{response.text[:100]}"
                    )

        return created

    def _get_color(self, label_name: str) -> str:
        for prefix, (color, _) in LABEL_COLORS.items():
            if label_name.startswith(prefix):
                return color
        return "ededed"

    def _get_description(self, label_name: str) -> str:
        for prefix, (_, description) in LABEL_COLORS.items():
            if label_name.startswith(prefix):
                value = label_name.split(":", 1)[-1]
                return f"{description}: {value}"
        return label_name
