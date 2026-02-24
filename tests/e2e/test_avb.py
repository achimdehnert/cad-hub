"""
E2E Tests: AVB (Ausschreibungs- und Vergabeprozess) Module — cad-hub (ADR-040).

Läuft gegen laufenden Docker-Container (Port 8094).
Ohne Login: nur Auth-Redirect-Verhalten prüfen.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8094"
pytestmark = pytest.mark.e2e


def test_avb_project_list_redirects_to_login(page: Page) -> None:
    page.goto(BASE_URL + "/avb/projects/")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/login/"))


def test_avb_project_list_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/avb/projects/")
    assert response is not None
    assert response.status < 500, f"Server error: {response.status}"


def test_avb_tender_list_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/avb/tenders/")
    assert response is not None
    assert response.status < 500


def test_avb_bidder_list_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/avb/bidders/")
    assert response is not None
    assert response.status < 500


def test_avb_project_create_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/avb/project/create/")
    assert response is not None
    assert response.status < 500


def test_avb_bidder_create_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/avb/bidder/create/")
    assert response is not None
    assert response.status < 500


def test_avb_tender_create_no_500(page: Page) -> None:
    response = page.goto(BASE_URL + "/avb/tender/create/")
    assert response is not None
    assert response.status < 500
