"""
E2E Tests: Authentication Flow (ADR-040).

Testet: Landing Page, Login, Logout, Redirect-Schutz.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


def test_landing_page_loads(page: Page, live_server) -> None:
    page.goto(live_server.url + "/")
    expect(page).to_have_title(re.compile(r"CAD|Hub|cad", re.IGNORECASE))


def test_login_page_renders(page: Page, live_server) -> None:
    page.goto(live_server.url + "/login/")
    expect(page.locator("[name=username]")).to_be_visible()
    expect(page.locator("[name=password]")).to_be_visible()
    expect(page.locator("[type=submit]")).to_be_visible()


def test_login_with_valid_credentials(auth_page: Page, live_server) -> None:
    expect(auth_page).not_to_have_url(live_server.url + "/login/")


def test_login_with_invalid_credentials(page: Page, live_server) -> None:
    page.goto(live_server.url + "/login/")
    page.fill("[name=username]", "wrong_user")
    page.fill("[name=password]", "wrong_pass")
    page.click("[type=submit]")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(live_server.url + "/login/")


def test_protected_page_redirects_to_login(page: Page, live_server) -> None:
    page.goto(live_server.url + "/avb/projects/")
    expect(page).to_have_url(re.compile(r"/login/"))


def test_health_endpoint_returns_200(page: Page, live_server) -> None:
    response = page.goto(live_server.url + "/livez/")
    assert response is not None
    assert response.status == 200
