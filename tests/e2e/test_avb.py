"""
E2E Tests: AVB (Ausschreibungs- und Vergabeprozess) Module (ADR-040).

Testet: Bauprojekte, Ausschreibungen, Bieter — CRUD-Flows.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


def test_avb_project_list_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/projects/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page).to_have_url(live_server.url + "/avb/projects/")
    expect(auth_page.locator("body")).to_be_visible()


def test_avb_project_create_page_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/project/create/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("form")).to_be_visible()


def test_avb_tender_list_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/tenders/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page).to_have_url(live_server.url + "/avb/tenders/")


def test_avb_bidder_list_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/bidders/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page).to_have_url(live_server.url + "/avb/bidders/")


def test_avb_bidder_create_page_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/bidder/create/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("form")).to_be_visible()


def test_avb_tender_create_page_renders(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/tender/create/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("form")).to_be_visible()


def test_avb_project_list_no_500(auth_page: Page, live_server) -> None:
    response = auth_page.goto(live_server.url + "/avb/projects/")
    assert response is not None
    assert response.status < 500, f"Server error: {response.status}"


def test_avb_navigation_links_present(auth_page: Page, live_server) -> None:
    auth_page.goto(live_server.url + "/avb/projects/")
    auth_page.wait_for_load_state("networkidle")
    expect(auth_page.locator("nav, header, [data-testid='nav']").first).to_be_visible()
