"""
E2E Tests: Authentication Flow — cad-hub (ADR-040).

Läuft gegen laufenden Docker-Container (Port 8094).
Kein live_server — cad-hub braucht PostgreSQL.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8094"
pytestmark = pytest.mark.e2e


def test_landing_page_loads(page: Page) -> None:
    response = page.goto(BASE_URL + "/")
    assert response is not None
    assert response.status < 500


def test_login_page_renders(page: Page) -> None:
    page.goto(BASE_URL + "/login/")
    expect(page.locator("[name=username]")).to_be_visible()
    expect(page.locator("[name=password]")).to_be_visible()
    expect(page.locator("[type=submit]")).to_be_visible()


def test_login_with_invalid_credentials(page: Page) -> None:
    page.goto(BASE_URL + "/login/")
    page.fill("[name=username]", "wrong_user")
    page.fill("[name=password]", "wrong_pass")
    page.click("[type=submit]")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/login/"))


def test_protected_page_redirects_to_login(page: Page) -> None:
    page.goto(BASE_URL + "/avb/projects/")
    expect(page).to_have_url(re.compile(r"/login/"))


def test_health_endpoint_returns_200(page: Page) -> None:
    response = page.goto(BASE_URL + "/livez/")
    assert response is not None
    assert response.status == 200


def test_readiness_endpoint_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/healthz/")
    assert response is not None
    assert response.status < 500


def test_admin_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/admin/")
    assert response is not None
    assert response.status < 500
