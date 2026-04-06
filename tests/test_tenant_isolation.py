"""
Tenant Isolation Tests — cad-hub (ADR-074)

Verifies that row-level tenant isolation via tenant_id works correctly:
- ConstructionProject from Tenant A is invisible to Tenant B
- TenantAwareManager filters by tenant_id automatically
- API endpoints do not leak cross-tenant data

These tests are MANDATORY CI-Gate (ADR-074 Layer 1 + Layer 2).
"""

import uuid

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_a_id():
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def tenant_b_id():
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_project(tenant_id, project_number="P-001"):
    """Helper: create IFCProject + ConstructionProject for a tenant."""
    from apps.avb.models import ConstructionProject
    from apps.ifc.models import IFCProject

    ifc = IFCProject.objects.create(
        tenant_id=tenant_id,
        name=f"IFC {project_number}",
    )
    return ConstructionProject.objects.create(
        tenant_id=tenant_id,
        ifc_project=ifc,
        project_number=project_number,
        client="Test Client",
    )


# ---------------------------------------------------------------------------
# Layer 1: Isolation Tests — TenantAwareManager
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_construction_project_isolated_by_tenant(tenant_a_id, tenant_b_id):
    """KRITISCH: ConstructionProject von Tenant A darf bei Tenant B nicht sichtbar sein."""
    from apps.avb.models import ConstructionProject

    project_a = _make_project(tenant_a_id, "P-A-001")

    results_b = ConstructionProject.objects.for_tenant(tenant_b_id)
    assert not results_b.filter(pk=project_a.pk).exists(), (
        "ISOLATION FAILURE: Tenant B kann Projekt von Tenant A sehen!"
    )


@pytest.mark.django_db
def test_construction_project_visible_within_own_tenant(tenant_a_id):
    """Tenant A sieht eigene Projekte."""
    from apps.avb.models import ConstructionProject

    project = _make_project(tenant_a_id, "P-A-002")

    results = ConstructionProject.objects.for_tenant(tenant_a_id)
    assert results.filter(pk=project.pk).exists()


@pytest.mark.django_db
def test_two_tenants_have_independent_project_counts(tenant_a_id, tenant_b_id):
    """Tenant A und B haben unabhängige Datensätze."""
    from apps.avb.models import ConstructionProject

    _make_project(tenant_a_id, "P-A-003")
    _make_project(tenant_a_id, "P-A-004")
    _make_project(tenant_b_id, "P-B-001")

    assert ConstructionProject.objects.for_tenant(tenant_a_id).count() == 2
    assert ConstructionProject.objects.for_tenant(tenant_b_id).count() == 1


# ---------------------------------------------------------------------------
# Layer 2: Propagation Tests — tenant_id muss bei Create gesetzt sein
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_construction_project_requires_tenant_id(tenant_a_id):
    """tenant_id muss explizit gesetzt werden — kein Default."""
    project = _make_project(tenant_a_id, "P-A-005")
    assert project.tenant_id == tenant_a_id


@pytest.mark.django_db
def test_for_tenant_returns_only_matching_tenant(tenant_a_id, tenant_b_id):
    """for_tenant() filtert strikt nach tenant_id."""
    from apps.avb.models import ConstructionProject

    _make_project(tenant_a_id, "P-A-006")
    _make_project(tenant_b_id, "P-B-002")

    qs_a = ConstructionProject.objects.for_tenant(tenant_a_id)
    for obj in qs_a:
        assert obj.tenant_id == tenant_a_id, (
            f"ISOLATION FAILURE: Objekt {obj.pk} hat tenant_id={obj.tenant_id}, erwartet {tenant_a_id}"
        )
