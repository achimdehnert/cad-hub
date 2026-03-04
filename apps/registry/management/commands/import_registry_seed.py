"""
Management Command: import_registry_seed

Importiert modules.json + profiles.json aus dem nl2cad-Repo als initialen
DB-Seed. Idempotent: bereits vorhandene Einträge werden aktualisiert (upsert).

Usage:
    python manage.py import_registry_seed
    python manage.py import_registry_seed --modules path/to/modules.json
    python manage.py import_registry_seed --profiles path/to/profiles.json
    python manage.py import_registry_seed --dry-run
"""
import json
import logging
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.registry.models import (
    BerufsProfil,
    DiscountRule,
    ModulePricing,
    NL2CADModule,
    ProfilModuleMapping,
)

logger = logging.getLogger(__name__)

DEFAULT_MODULES_PATH = Path(__file__).resolve().parents[6] / "nl2cad" / "docs" / "data" / "modules.json"
DEFAULT_PROFILES_PATH = Path(__file__).resolve().parents[6] / "nl2cad" / "docs" / "data" / "profiles.json"


class Command(BaseCommand):
    help = "Importiert nl2cad modules.json + profiles.json als DB-Seed (idempotent)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--modules",
            type=Path,
            default=DEFAULT_MODULES_PATH,
            help="Pfad zu modules.json",
        )
        parser.add_argument(
            "--profiles",
            type=Path,
            default=DEFAULT_PROFILES_PATH,
            help="Pfad zu profiles.json",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur validieren, nichts speichern",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        modules_path: Path = options["modules"]
        profiles_path: Path = options["profiles"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — keine Änderungen werden gespeichert"))

        # ── Module ──────────────────────────────────────────────────────────
        if modules_path.exists():
            self._import_modules(modules_path, dry_run)
        else:
            self.stdout.write(
                self.style.WARNING(f"modules.json nicht gefunden: {modules_path}")
            )

        # ── Profile ─────────────────────────────────────────────────────────
        if profiles_path.exists():
            self._import_profiles(profiles_path, dry_run)
        else:
            self.stdout.write(
                self.style.WARNING(f"profiles.json nicht gefunden: {profiles_path} — übersprungen")
            )

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("Registry-Seed erfolgreich importiert."))

    def _import_modules(self, path: Path, dry_run: bool) -> None:
        self.stdout.write(f"Module importieren aus: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))

        modules_data = data.get("modules", [])
        self.stdout.write(f"  {len(modules_data)} Module gefunden")

        # Discount-Regel anlegen / aktualisieren
        if not dry_run:
            DiscountRule.objects.update_or_create(
                min_modules=data.get("discount_threshold", 3),
                defaults={
                    "name":             f"Standard-Rabatt ab {data.get('discount_threshold', 3)} Modulen",
                    "discount_percent": Decimal(str(data.get("discount_percent", 15))),
                    "is_active":        True,
                },
            )

        for i, m in enumerate(modules_data):
            module_id = m["id"]
            pricing = m.get("pricing", {})

            if dry_run:
                self.stdout.write(f"  [DRY] Modul: {module_id} — {m.get('name')}")
                continue

            obj, created = NL2CADModule.objects.update_or_create(
                id=module_id,
                defaults={
                    "package":       m.get("package", ""),
                    "name":          m.get("name", ""),
                    "icon":          m.get("icon", "📦"),
                    "color":         m.get("color", "#2563eb"),
                    "tagline":       m.get("tagline", ""),
                    "description":   m.get("description", ""),
                    "features":      m.get("features", []),
                    "deps":          m.get("deps", []),
                    "norms":         m.get("norms", []),
                    "main_classes":  m.get("main_classes", []),
                    "is_required":   m.get("required", False),
                    "status":        m.get("status", "planned"),
                    "priority":      _map_priority(m.get("priority", "medium")),
                    "story_points":  m.get("story_points", 0),
                    "target_quarter": m.get("target_quarter", ""),
                    "adr_path":      m.get("adr") or "",
                    "workflow_path": m.get("workflow") or "",
                    "pypi_url":      m.get("pypi") or "",
                    "sort_order":    i,
                },
            )

            # Standard-Preis anlegen / aktualisieren
            ModulePricing.objects.update_or_create(
                module=obj,
                organization=None,
                defaults={
                    "pricing_type": "free" if pricing.get("monthly_eur", 0) == 0 else "standard",
                    "setup_eur":    Decimal(str(pricing.get("setup_eur", 0))),
                    "monthly_eur":  Decimal(str(pricing.get("monthly_eur", 0))),
                    "label":        pricing.get("label", ""),
                },
            )

            verb = "angelegt" if created else "aktualisiert"
            self.stdout.write(f"  ✓ {module_id} {verb}")

    def _import_profiles(self, path: Path, dry_run: bool) -> None:
        self.stdout.write(f"Berufsprofile importieren aus: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))

        profiles_data = data.get("profiles", [])
        self.stdout.write(f"  {len(profiles_data)} Profile gefunden")

        for i, p in enumerate(profiles_data):
            profil_id = p["id"]

            if dry_run:
                self.stdout.write(f"  [DRY] Profil: {profil_id} — {p.get('name')}")
                continue

            obj, created = BerufsProfil.objects.update_or_create(
                id=profil_id,
                defaults={
                    "name":            p.get("name", ""),
                    "icon":            p.get("icon", "👤"),
                    "fokus":           p.get("fokus", ""),
                    "bereitschaft":    p.get("bereitschaft", ""),
                    "install_command": p.get("install", ""),
                    "yaml_config":     p.get("yaml_config", ""),
                    "nlp_keywords":    ", ".join(p.get("nlp_keywords", [])),
                    "report_template": p.get("report_template", ""),
                    "primary_output":  p.get("primary_output", ""),
                    "sort_order":      i,
                },
            )

            # Modul-Zuordnungen
            for mapping in p.get("modules", []):
                try:
                    module = NL2CADModule.objects.get(id=mapping["id"])
                except NL2CADModule.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Modul '{mapping['id']}' nicht gefunden — übersprungen"
                        )
                    )
                    continue

                ProfilModuleMapping.objects.update_or_create(
                    profil=obj,
                    module=module,
                    defaults={
                        "mapping_type":  mapping.get("mapping_type", "neu"),
                        "is_recommended": mapping.get("recommended", True),
                    },
                )

            verb = "angelegt" if created else "aktualisiert"
            self.stdout.write(f"  ✓ {profil_id} {verb}")


def _map_priority(value: str) -> str:
    mapping = {
        "hoch":    "high",
        "mittel":  "medium",
        "niedrig": "low",
        "high":    "high",
        "medium":  "medium",
        "low":     "low",
    }
    return mapping.get(value.lower(), "medium")
