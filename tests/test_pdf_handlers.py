"""Tests für die PDF-Handler in apps/dxf/handlers/ (Issue #68).

Die drei Handler lagen ohne Aufrufer und ohne Test im Repo; PyMuPDF war nicht
deklariert, der Import stand lazy in der Funktion. Sie waren damit nie
ausgeführt worden. Diese Datei ist der Nachweis, dass sie laufen.

**Zu den Fixtures.** Die PDFs hier sind *synthetisch* — sie werden zur Laufzeit
mit PyMuPDF erzeugt und tragen erfundene Werte. Das ist bewusst: ein echter
Lageplan enthält Namen und Anschriften von Bauherren und Nachbarn und gehört
nicht in ein Repo. Der Preis dafür ist, dass diese Tests die *Erkennungslogik*
gegen saubere Beschriftung prüfen, nicht gegen die Streuung echter Pläne.
Gegen echte Pläne ist getrennt zu messen, bevor jemand den Zahlen vertraut.
"""

import pymupdf
import pytest
from django.urls import reverse

from apps.dxf.handlers import (
    PDFAbstandsflaechenHandler,
    PDFLageplanHandler,
    PDFVisionHandler,
)

# Kein importorskip: pymupdf ist seit Issue #68 eine deklarierte Abhaengigkeit.
# Ein Ueberspringen wuerde genau den Zustand wieder herstellen, den dieses Issue
# beseitigt — gruen, weil nichts lief.

# Echte Umlaute sind hier Absicht, nicht Kosmetik: die Erkennungsmuster der
# Handler verlangen sie (z. B. r"Fl(?:ur)?st(?:ück)?"). Eine ASCII-Umschrift
# ("Flurstueck") wird NICHT erkannt — beim ersten Lauf dieser Tests ist genau
# das aufgefallen. Fuer CAD-Export aus dem Planungsbuero ist das unkritisch,
# fuer Scans mit schwacher OCR nicht.
LAGEPLAN_TEXT = """\
Lageplan zum Bauantrag
Maßstab 1:500
Nordrichtung: Nord
Gemarkung: Musterhausen
Flurstück: 1234/5
Grundstücksfläche: 850,00 m²
GRZ: 0,35
GFZ: 0,70
Grenzabstand: 3,50 m
4 Stellplätze
"""

ABSTANDSFLAECHEN_TEXT = """\
Abstandsflächenplan
Maßstab 1:200
Nordseite
Wandhöhe: 6,50 m
0,4 x H = 2,60 m
Abstandsfläche: 2,60 m
"""


def _pdf_bytes(text: str) -> bytes:
    """Erzeugt ein einseitiges Text-PDF mit PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 80), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


# --------------------------------------------------------------------------
# Handler
# --------------------------------------------------------------------------


def test_should_extract_lageplan_fields_from_pdf():
    result = PDFLageplanHandler().execute(
        {"pdf_content": _pdf_bytes(LAGEPLAN_TEXT), "use_llm": False}
    )

    assert result.success, result.errors
    lageplan = result.data["lageplan"]
    assert lageplan["grundstueck"]["flurstueck"] == "1234/5"
    assert lageplan["grundstueck"]["gemarkung"].startswith("Musterhausen")
    assert lageplan["kennzahlen"]["grz"] == pytest.approx(0.35)
    assert lageplan["kennzahlen"]["gfz"] == pytest.approx(0.70)
    # Der WERT, nicht nur seine Anwesenheit: `assert lageplan["massstab"]` hat
    # den Fehler aus Issue #73 (`1:1:500`) monatelang durchgelassen.
    assert lageplan["massstab"] == "1:500"
    assert lageplan["stellplaetze"] == 4


@pytest.mark.parametrize(
    "fund, erwartet",
    [
        ("500", "1:500"),  # „M. 500" — Gruppe ohne Doppelpunkt
        ("1:500", "1:500"),  # „Maßstab 1:500" — Gruppe MIT Doppelpunkt
        ("1 : 500", "1:500"),  # mit Leerzeichen gesetzt
        ("1:1000", "1:1000"),
        ("2:500", "2:500"),  # kein stilles Ueberschreiben des Zaehlers
    ],
)
def test_should_normalise_the_scale_without_doubling_the_prefix(fund, erwartet):
    """Issue #73: die Zuweisung stellte `1:` unbedingt voran und erzeugte
    aus einer Fundstelle mit Doppelpunkt `1:1:500`."""
    from apps.dxf.handlers.pdf_lageplan import _massstab_normieren

    assert _massstab_normieren(fund) == erwartet


def test_should_extract_abstandsflaechen_from_pdf():
    result = PDFAbstandsflaechenHandler().execute(
        {"pdf_content": _pdf_bytes(ABSTANDSFLAECHEN_TEXT), "use_llm": False}
    )

    assert result.success, result.errors
    assert "abstandsflaechen" in result.data


def test_should_report_error_when_no_pdf_given():
    result = PDFLageplanHandler().execute({})

    assert not result.success
    assert any("pdf" in e.lower() for e in result.errors)


def test_should_report_error_when_pdf_is_not_a_pdf():
    result = PDFLageplanHandler().execute({"pdf_content": b"kein PDF, nur Text", "use_llm": False})

    assert not result.success
    assert result.errors


def test_should_not_call_cloud_when_vision_handler_has_no_key(monkeypatch):
    """PDFVisionHandler ist nicht verdrahtet (ADR-089) und darf ohne Schluessel
    nicht ins Netz gehen — er soll sauber melden statt zu versuchen."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = PDFVisionHandler().execute({"pdf_content": _pdf_bytes(LAGEPLAN_TEXT)})

    # Ohne Schluessel gibt es kein Analyseergebnis; entscheidend ist, dass der
    # Handler das meldet und nicht mit einer Exception aus dem Prozess faellt.
    assert result.status is not None
    assert not result.success or result.warnings or result.errors


# --------------------------------------------------------------------------
# Endpunkte
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_analyze_lageplan_via_endpoint(client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile(
        "lageplan.pdf", _pdf_bytes(LAGEPLAN_TEXT), content_type="application/pdf"
    )
    response = client.post(reverse("dxf:pdf_lageplan"), {"file": upload})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["use_llm"] is False, "LLM darf ohne Anforderung nicht laufen"
    assert payload["lageplan"]["grundstueck"]["flurstueck"] == "1234/5"


@pytest.mark.django_db
def test_should_reject_endpoint_call_without_file(client):
    response = client.post(reverse("dxf:pdf_lageplan"), {})

    assert response.status_code == 400


@pytest.mark.django_db
def test_should_reject_endpoint_call_with_non_pdf(client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("plan.dxf", b"0\nSECTION\n", content_type="text/plain")
    response = client.post(reverse("dxf:pdf_lageplan"), {"file": upload})

    assert response.status_code == 400


def test_should_not_expose_vision_handler_as_endpoint():
    """Positivkontrolle zur Regel im urls.py-Kommentar: es gibt keinen
    Vision-Endpunkt. Faellt dieser Test, wurde ADR-089 stillschweigend
    aufgeweicht."""
    from django.urls import NoReverseMatch

    with pytest.raises(NoReverseMatch):
        reverse("dxf:pdf_vision")


# --------------------------------------------------------------------------
# Der Aufrufer (Issue #68, zweite Runde)
# --------------------------------------------------------------------------
# Die Tests oben laufen mit Djangos Test-Client, der die CSRF-Pruefung
# standardmaessig abschaltet. Genau deshalb waren sie gruen, waehrend ein
# `POST` gegen nl2cad.de mit 403 antwortete: es gab keine Seite, die einen
# Token mitbringt. Die Tests hier schliessen diese Luecke — einer prueft die
# Seite, einer den Weg MIT eingeschalteter CSRF-Pruefung.


@pytest.mark.django_db
def test_should_analyze_abstandsflaechen_via_endpoint(client):
    """Fehlte bisher: nur der Lageplan-Endpunkt war ueber HTTP geprueft."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile(
        "abstand.pdf",
        _pdf_bytes(ABSTANDSFLAECHEN_TEXT),
        content_type="application/pdf",
    )
    response = client.post(reverse("dxf:pdf_abstandsflaechen"), {"file": upload})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "abstandsflaechen" in payload


@pytest.mark.django_db
def test_should_serve_a_page_that_calls_both_endpoints(client):
    """Ohne Aufrufer sind die Endpunkte tot — das war der Befund aus #68."""
    response = client.get(reverse("dxf:pdf_auswertung"))

    assert response.status_code == 200
    seite = response.content.decode()
    assert reverse("dxf:pdf_lageplan") in seite
    assert reverse("dxf:pdf_abstandsflaechen") in seite
    assert "X-CSRFToken" in seite, "die Seite muss den Token mitschicken"


@pytest.mark.django_db
def test_should_accept_the_upload_when_csrf_is_enforced():
    """Der Test, der den Produktions-403 gefunden haette.

    `enforce_csrf_checks=True` schaltet die Pruefung ein, die der normale
    Test-Client umgeht. Der Token kommt aus der Seite — genau der Weg, den ein
    Browser nimmt.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client

    streng = Client(enforce_csrf_checks=True)
    seite = streng.get(reverse("dxf:pdf_auswertung"))
    token = seite.cookies["csrftoken"].value

    upload = SimpleUploadedFile(
        "lageplan.pdf", _pdf_bytes(LAGEPLAN_TEXT), content_type="application/pdf"
    )
    response = streng.post(reverse("dxf:pdf_lageplan"), {"file": upload}, HTTP_X_CSRFTOKEN=token)

    assert response.status_code == 200, (
        "mit Token muss der Upload durchgehen — sonst ist die Seite kein Aufrufer"
    )


@pytest.mark.django_db
def test_should_reject_the_upload_when_csrf_token_is_missing():
    """Gegenprobe: ohne Token weist die Pruefung ab. Ohne diesen Test waere
    der Test darueber nicht von einer abgeschalteten Pruefung zu unterscheiden.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client

    streng = Client(enforce_csrf_checks=True)
    upload = SimpleUploadedFile(
        "lageplan.pdf", _pdf_bytes(LAGEPLAN_TEXT), content_type="application/pdf"
    )
    response = streng.post(reverse("dxf:pdf_lageplan"), {"file": upload})

    assert response.status_code == 403
