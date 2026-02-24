"""
Playwright E2E Fixtures für cad-hub (ADR-040).

Stellt authentifizierte Browser-Sessions für AVB-Tests bereit.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from playwright.sync_api import Page, expect


@pytest.fixture
def cad_user(db):
    """Test-User für cad-hub E2E Tests."""
    return User.objects.create_user(
        username="e2e_test",
        email="e2e@cadtest.local",
        password="testpass123!",
        is_active=True,
    )


@pytest.fixture
def auth_page(page: Page, cad_user, live_server) -> Page:
    """Playwright Page mit eingeloggtem cad-hub User."""
    page.goto(f"{live_server.url}/login/")
    page.fill("[name=username]", cad_user.username)
    page.fill("[name=password]", "testpass123!")
    page.click("[type=submit]")
    page.wait_for_load_state("networkidle")
    return page


def assert_testid_visible(page: Page, testid: str) -> None:
    expect(page.locator(f"[data-testid='{testid}']")).to_be_visible()
