"""Tests für apps.vorgang — Vorgang/Dokument/Befund (Issue #72 K4, #77).

**Zu den Fixtures.** Der Lageplan-Text ist synthetisch (wie in
tests/test_pdf_handlers.py) — erfundene Werte, zur Laufzeit per PyMuPDF in
ein PDF gerendert. Kein echter Bauantrag, keine Personendaten (Repo ist
öffentlich).

**Ablage.** Der Auftrag sah ``apps/vorgang/tests/`` vor; der tatsächliche
Bestand (``pytest.ini``: ``testpaths = tests``, höhere Priorität als
``pyproject.toml``) sammelt nur aus dem Wurzel-``tests/``-Verzeichnis — dort
liegen auch alle anderen Testdateien des Repos. Diese Datei folgt dem
Bestand.
"""

import datetime
import hashlib

import pymupdf
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django_tenancy.models import Membership, Organization

from apps.vorgang.models import Befund, Vorgang, VorgangRolle
from apps.vorgang.services import (
    haenge_dokument_an,
    lege_vorgang_an,
    loesche_abgelaufene_vorgaenge,
    pruefe_lageplan,
)

User = get_user_model()

LAGEPLAN_TEXT = """\
Lageplan zum Bauantrag
Maßstab 1:500
Flurstück: 123/4
Gemarkung: Musterhausen
Grundstücksfläche: 700,00 m²
"""


def _pdf_bytes(text: str) -> bytes:
    """Erzeugt ein einseitiges Text-PDF mit PyMuPDF (Muster: test_pdf_handlers.py)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 80), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def _pdf_upload(name: str = "lageplan.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, _pdf_bytes(LAGEPLAN_TEXT), content_type="application/pdf")


# ---------------------------------------------------------------------------
# Fixtures — Organisation/Mitgliedschaft (Muster: tests/test_tenancy_membership_guard.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def organisation(db):
    return Organization.objects.create(name="Testbüro", slug="testbuero", status="active")


@pytest.fixture
def fremde_organisation(db):
    return Organization.objects.create(name="Fremdbüro", slug="fremdbuero", status="active")


@pytest.fixture
def mitglied(db, organisation):
    user = User.objects.create_user(username="sachbearbeiter", password="p")
    Membership.objects.create(
        tenant_id=organisation.tenant_id, organization=organisation, user=user
    )
    return user


def _tenant_header(organisation) -> dict:
    """SubdomainTenantMiddleware fällt beim Test-Client (Host 'testserver',
    keine Subdomain) auf den Header X-Tenant-ID zurück."""
    return {"HTTP_X_TENANT_ID": str(organisation.tenant_id)}


# ---------------------------------------------------------------------------
# 1. Anonymer Zugriff
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_reject_anonymous_upload(client, organisation):
    vorgang = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=None,
        art="bauantrag",
        titel="Anonymer Zugriffstest",
        rolle=VorgangRolle.SACHBEARBEITUNG,
    )

    pdf_antwort = client.post(reverse("dxf:pdf_lageplan"), {"file": _pdf_upload()})
    assert pdf_antwort.status_code in (302, 403)
    assert pdf_antwort.status_code != 200

    upload_antwort = client.post(
        reverse("vorgang:dokument_upload", args=[vorgang.pk]),
        {"datei": _pdf_upload()},
    )
    assert upload_antwort.status_code in (302, 403)
    assert upload_antwort.status_code != 200


# ---------------------------------------------------------------------------
# 2. Mandantentrennung
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_isolate_tenants(client, organisation, fremde_organisation, mitglied):
    fremder_vorgang = lege_vorgang_an(
        tenant_id=fremde_organisation.tenant_id,
        user=None,
        art="bauantrag",
        titel="Vorgang von Mandant B",
        rolle=VorgangRolle.SACHBEARBEITUNG,
    )

    client.force_login(mitglied)
    header = _tenant_header(organisation)

    liste = client.get(reverse("vorgang:vorgang_list"), **header)
    assert liste.status_code == 200
    assert fremder_vorgang not in list(liste.context["vorgaenge"])

    detail = client.get(reverse("vorgang:vorgang_detail", args=[fremder_vorgang.pk]), **header)
    assert detail.status_code == 404


# ---------------------------------------------------------------------------
# 3. Nur PDF
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_reject_non_pdf(organisation, mitglied):
    vorgang = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=mitglied,
        art="bauantrag",
        titel="Nur PDF",
        rolle=VorgangRolle.SACHBEARBEITUNG,
    )

    with pytest.raises(ValueError):
        haenge_dokument_an(
            vorgang, SimpleUploadedFile("notiz.txt", b"kein PDF", content_type="text/plain")
        )

    assert vorgang.dokumente.count() == 0


# ---------------------------------------------------------------------------
# 4. sha256 + Seitenzahl
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_store_sha256_and_pages(organisation, mitglied):
    vorgang = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=mitglied,
        art="bauantrag",
        titel="Hash + Seiten",
        rolle=VorgangRolle.SACHBEARBEITUNG,
    )
    inhalt = _pdf_bytes(LAGEPLAN_TEXT)

    dokument = haenge_dokument_an(
        vorgang, SimpleUploadedFile("lageplan.pdf", inhalt, content_type="application/pdf")
    )

    assert dokument.sha256 == hashlib.sha256(inhalt).hexdigest()
    assert dokument.seiten is not None
    assert dokument.seiten >= 1


# ---------------------------------------------------------------------------
# 5. Befunde aus Lageplan
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_create_befunde_from_lageplan(organisation, mitglied):
    vorgang = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=mitglied,
        art="bauantrag",
        titel="Lageplan-Befunde",
        rolle=VorgangRolle.SACHBEARBEITUNG,
    )
    dokument = haenge_dokument_an(vorgang, _pdf_upload())

    befunde = pruefe_lageplan(dokument)

    assert len(befunde) >= 2
    assert all(b.regel_id.startswith("lageplan.") for b in befunde)
    dokument.refresh_from_db()
    assert dokument.vorlagenart == "lageplan"


# ---------------------------------------------------------------------------
# 6. Löschfrist Pflicht für Einreicher (#77)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_require_loeschfrist_for_einreicher(organisation):
    with pytest.raises(ValueError):
        lege_vorgang_an(
            tenant_id=organisation.tenant_id,
            user=None,
            art="bauantrag",
            titel="Einreicher ohne Frist",
            rolle=VorgangRolle.EINREICHER,
        )


# ---------------------------------------------------------------------------
# 7. Löschung nur mit ausfuehren=True
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_delete_expired_only_when_executed(organisation):
    heute = datetime.date.today()

    abgelaufen = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=None,
        art="bauantrag",
        titel="Abgelaufen",
        rolle=VorgangRolle.EINREICHER,
        loeschfrist_am=heute - datetime.timedelta(days=1),
    )
    haenge_dokument_an(abgelaufen, _pdf_upload("abgelaufen.pdf"))

    gueltig = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=None,
        art="bauantrag",
        titel="Noch gültig",
        rolle=VorgangRolle.EINREICHER,
        loeschfrist_am=heute + datetime.timedelta(days=30),
    )

    trockenlauf = loesche_abgelaufene_vorgaenge(heute, ausfuehren=False)
    assert abgelaufen.pk in trockenlauf
    assert gueltig.pk not in trockenlauf
    assert Vorgang.objects.filter(pk=abgelaufen.pk).exists(), "Dry-Run darf nichts löschen"

    ausgefuehrt = loesche_abgelaufene_vorgaenge(heute, ausfuehren=True)
    assert abgelaufen.pk in ausgefuehrt
    assert not Vorgang.objects.filter(pk=abgelaufen.pk).exists()
    assert Vorgang.objects.filter(pk=gueltig.pk).exists()


# ---------------------------------------------------------------------------
# 8. Befund-Status per HTMX umschalten
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_should_toggle_befund_status(client, organisation, mitglied):
    vorgang = lege_vorgang_an(
        tenant_id=organisation.tenant_id,
        user=mitglied,
        art="bauantrag",
        titel="Status-Toggle",
        rolle=VorgangRolle.SACHBEARBEITUNG,
    )
    befund = Befund.objects.create(
        tenant_id=organisation.tenant_id,
        vorgang=vorgang,
        regel_id="lageplan.massstab",
        wert="1:500",
    )

    client.force_login(mitglied)
    antwort = client.post(
        reverse("vorgang:befund_status", args=[befund.pk]),
        {"status": "bestaetigt"},
        HTTP_HX_REQUEST="true",
        **_tenant_header(organisation),
    )

    assert antwort.status_code == 200
    assert "bestaetigt" in antwort.content.decode()
    befund.refresh_from_db()
    assert befund.status == "bestaetigt"
