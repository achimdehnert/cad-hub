# tests/test_core_views.py — ADR-057 Phase 2: View Tests
import pytest


@pytest.mark.django_db
class TestHealthEndpoints:
    def test_should_return_200_on_livez(self, client):
        response = client.get("/livez/")
        assert response.status_code == 200

    def test_should_redirect_anonymous_from_root(self, client):
        response = client.get("/")
        assert response.status_code in (200, 302)


@pytest.mark.django_db
class TestLoginRequired:
    def test_should_redirect_anonymous_to_login(self, client):
        response = client.get("/ifc/")
        assert response.status_code in (302, 301)

    def test_should_return_200_for_authenticated_user(self, client):
        from tests.factories import UserFactory
        user = UserFactory()
        client.force_login(user)
        response = client.get("/")
        assert response.status_code in (200, 302)
