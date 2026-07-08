"""
Management Command: diff_room_detection

Temporäres Diagnose-Werkzeug für die ADR-012-T2-Migration (nl2cad-core
DXFParser ersetzt FloorPlanAnalyzer für die Raumerkennung). Läuft den alten
(FloorPlanAnalyzer) und den neuen (nl2cad DXFParser) Pfad gegen dieselbe
DXF-Datei und meldet Abweichungen in Raum-Anzahl/Namen/Flächen — der
Verhaltens-Wechsel (andere Extraktionsstrategien) muss vor PR 2 sichtbar
gemacht werden, nicht erst in Prod auffallen.

Zu entfernen in PR 3 zusammen mit FloorPlanAnalyzer.identify_rooms()/
calculate_room_areas() (siehe docs/AGENT_HANDOVER.md ADR-012-T2-Plan).

Usage:
    python manage.py diff_room_detection path/to/file.dxf [path/to/other.dxf ...]
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.dxf.services.cad_loader import CADLoaderService


class Command(BaseCommand):
    help = "Vergleicht FloorPlanAnalyzer (alt) vs. nl2cad DXFParser (neu) Raumerkennung."

    def add_arguments(self, parser):
        parser.add_argument("dxf_files", nargs="+", type=str)

    def handle(self, *args, **options):
        had_mismatch = False
        for raw_path in options["dxf_files"]:
            path = Path(raw_path)
            if not path.exists():
                raise CommandError(f"Datei nicht gefunden: {path}")

            self.stdout.write(self.style.MIGRATE_HEADING(f"=== {path.name} ==="))
            loader = CADLoaderService.from_file(path)

            old_rooms = loader.floor_analyzer.identify_rooms()
            old_areas = loader.floor_analyzer.calculate_room_areas()
            new_rooms = loader.dxf_model.rooms

            old_names = sorted(r["name"] for r in old_rooms if r.get("name"))
            new_names = sorted(r.name for r in new_rooms if r.name)

            self.stdout.write(
                f"  Räume:  alt={len(old_rooms)} (Text-Match)  "
                f"neu={len(new_rooms)} (Polygon+Text)  "
                f"Flächen-alt={len(old_areas)} (raw units)"
            )

            only_old = sorted(set(old_names) - set(new_names))
            only_new = sorted(set(new_names) - set(old_names))
            if only_old:
                self.stdout.write(self.style.WARNING(f"  Nur alt erkannt: {only_old}"))
                had_mismatch = True
            if only_new:
                self.stdout.write(self.style.WARNING(f"  Nur neu erkannt: {only_new}"))
                had_mismatch = True

            for r in new_rooms:
                self.stdout.write(
                    f"    - {r.name or '(unbenannt)'} [{r.layer}]: "
                    f"{r.area_m2:.2f} m², Umfang {r.perimeter_m:.2f} m, "
                    f"{len(r.vertices)} Vertices"
                )

        if had_mismatch:
            self.stdout.write(
                self.style.WARNING(
                    "\nAbweichungen gefunden — vor PR 2 manuell gegen echte Uploads prüfen."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nKeine Namens-Abweichungen gefunden."))
