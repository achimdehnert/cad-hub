"""Vorgang services — reine Funktionen, keine Logik in Views.

Konvention (docs/AGENT_HANDOVER.md): views.py → services.py → models.py.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
from collections.abc import Iterable

from .models import Befund, BefundStatus, Dokument, Vorgang, VorgangRolle

logger = logging.getLogger(__name__)


def lege_vorgang_an(
    *,
    tenant_id,
    user,
    art: str,
    titel: str,
    rolle: str,
    loeschfrist_am: datetime.date | None = None,
) -> Vorgang:
    """Legt einen neuen Vorgang an.

    Bei Rolle ``einreicher`` ist die Löschfrist Pflicht (#77 — die
    Vorprüfung vor Einreichung verarbeitet Unterlagen Dritter). Erzwungen
    hier im Service, nicht per DB-Constraint (semantische Regel, gilt nur
    für eine Rolle).
    """
    if rolle == VorgangRolle.EINREICHER and not loeschfrist_am:
        raise ValueError("Vorgänge der Rolle 'einreicher' brauchen eine Löschfrist (#77).")

    return Vorgang.objects.create(
        tenant_id=tenant_id,
        art=art,
        titel=titel,
        eingereicht_von_rolle=rolle,
        loeschfrist_am=loeschfrist_am,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )


def _sha256(daten: bytes) -> str:
    return hashlib.sha256(daten).hexdigest()


def _seitenzahl(daten: bytes) -> int | None:
    """Seitenzahl per PyMuPDF; ``None`` wenn nicht ermittelbar.

    Import-Name ist ``pymupdf`` (nicht ``fitz`` — das alte Modul ist
    deprecated, siehe requirements.txt und apps/dxf/handlers/pdf_lageplan.py).
    """
    try:
        import pymupdf
    except ImportError:
        return None

    try:
        doc = pymupdf.open(stream=daten, filetype="pdf")
        anzahl = doc.page_count
        doc.close()
        return anzahl
    except Exception:  # noqa: BLE001 - Seitenzahl ist best-effort, kein harter Fehler
        logger.warning("Seitenzahl konnte nicht ermittelt werden.", exc_info=True)
        return None


def haenge_dokument_an(vorgang: Vorgang, uploaded_file) -> Dokument:
    """Hängt ein Dokument an einen Vorgang. Nur PDF ist erlaubt."""
    dateiname = uploaded_file.name
    if not dateiname.lower().endswith(".pdf"):
        raise ValueError("Nur PDF-Dateien sind erlaubt.")

    inhalt = uploaded_file.read()
    uploaded_file.seek(0)

    return Dokument.objects.create(
        tenant_id=vorgang.tenant_id,
        vorgang=vorgang,
        datei=uploaded_file,
        dateiname=dateiname,
        sha256=_sha256(inhalt),
        seiten=_seitenzahl(inhalt),
    )


def _flache_lageplan_felder(lageplan: dict) -> Iterable[tuple[str, object]]:
    """Iteriert die Top-Level-Felder von ``LageplanInfo.to_dict()`` flach.

    ``gebaeude`` ist eine Liste (mehrere Gebäude je Grundstück) und liefert
    keinen einzelnen Skalarwert — wird hier ausgelassen, nicht befundet.
    """
    for schluessel, wert in lageplan.items():
        if schluessel == "gebaeude":
            continue
        if isinstance(wert, dict):
            for teil_schluessel, teil_wert in wert.items():
                yield f"{schluessel}.{teil_schluessel}", teil_wert
        else:
            yield schluessel, wert


def pruefe_lageplan(dokument: Dokument) -> list[Befund]:
    """Prüft ein Dokument als Lageplan und legt je gefundenem Feld einen Befund an."""
    from apps.dxf.handlers.pdf_lageplan import PDFLageplanHandler

    with dokument.datei.open("rb") as datei_handle:
        pdf_bytes = datei_handle.read()

    result = PDFLageplanHandler().execute({"pdf_content": pdf_bytes, "use_llm": False})

    dokument.vorlagenart = "lageplan"
    dokument.save(update_fields=["vorlagenart", "updated_at"])

    if not result.success:
        fehler_befund = Befund.objects.create(
            tenant_id=dokument.tenant_id,
            vorgang=dokument.vorgang,
            dokument=dokument,
            regel_id="lageplan.fehler",
            wert="; ".join(result.errors),
            status=BefundStatus.OFFEN,
        )
        return [fehler_befund]

    lageplan = result.data.get("lageplan", {})
    neue_befunde = [
        Befund(
            tenant_id=dokument.tenant_id,
            vorgang=dokument.vorgang,
            dokument=dokument,
            regel_id=f"lageplan.{feld}",
            feld=feld,
            wert=str(wert),
        )
        for feld, wert in _flache_lageplan_felder(lageplan)
        if wert not in (None, "", 0, 0.0)
    ]
    if not neue_befunde:
        return []
    return Befund.objects.bulk_create(neue_befunde)


def setze_befund_status(befund: Befund, status: str) -> Befund:
    befund.status = status
    befund.save(update_fields=["status", "updated_at"])
    return befund


def loesche_abgelaufene_vorgaenge(stichtag: datetime.date, ausfuehren: bool = False) -> list:
    """Findet (Dry-Run) bzw. löscht (``ausfuehren=True``) Vorgänge mit abgelaufener Löschfrist.

    Gibt in beiden Fällen die Liste der (gefundenen bzw. gelöschten) IDs zurück.
    """
    abgelaufen_ids = list(
        Vorgang.objects.filter(loeschfrist_am__lt=stichtag).values_list("id", flat=True)
    )

    if not ausfuehren:
        return abgelaufen_ids

    for vorgang in Vorgang.objects.filter(id__in=abgelaufen_ids):
        for dokument in vorgang.dokumente.all():
            if dokument.datei:
                dokument.datei.delete(save=False)
        vorgang.delete()

    return abgelaufen_ids
