"""Management Command: vorgang_loeschen_abgelaufen (#72 K4, Löschfrist aus #77).

Dry-Run per Default — löscht nur mit ``--ausfuehren``. Ist unabhängig von
der Vorgangs-Rolle: jeder Vorgang mit gesetzter (abgelaufener) Löschfrist
wird erfasst, nicht nur die künftige Einreicher-Rolle aus #77.
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.vorgang import services


class Command(BaseCommand):
    help = "Findet (Dry-Run) bzw. löscht (--ausfuehren) Vorgänge mit abgelaufener Löschfrist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ausfuehren",
            action="store_true",
            help="Tatsächlich löschen (Default: Dry-Run, nur anzeigen).",
        )

    def handle(self, *args, **options):
        ausfuehren = options["ausfuehren"]
        ids = services.loesche_abgelaufene_vorgaenge(date.today(), ausfuehren=ausfuehren)

        if not ids:
            self.stdout.write("Keine abgelaufenen Vorgänge gefunden.")
            return

        modus = "gelöscht" if ausfuehren else "gefunden (Dry-Run — mit --ausfuehren löschen)"
        self.stdout.write(f"{len(ids)} Vorgang/Vorgänge {modus}:")
        for vorgang_id in ids:
            self.stdout.write(f"  - {vorgang_id}")
