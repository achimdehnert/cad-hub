"""Auth + access control tests for cad-hub (ADR-058 A2)."""

import pytest
from platform_context.testing.assertions import assert_login_required, assert_no_data_leak

PROTECTED_URLS = [
    "/ifc/",
    "/avb/projects/",
    "/admin/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", PROTECTED_URLS)
def test_should_protected_url_require_login(client, url):
    """A2: All protected URLs redirect unauthenticated users to login."""
    assert_login_required(client, url)


@pytest.mark.django_db
def test_should_authenticated_user_reach_dashboard(auth_client):
    """U1: Authenticated user can access dashboard."""
    response = auth_client.get("/ifc/")
    assert response.status_code in (200, 302)


@pytest.mark.django_db
def test_should_health_endpoint_be_public(client):
    """U9: /livez/ is reachable without authentication."""
    response = client.get("/livez/")
    assert response.status_code == 200
