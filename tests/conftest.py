# tests/conftest.py
import pytest
from django.contrib.auth import get_user_model

# Exclude e2e tests (require playwright) from default collection
collect_ignore_glob = ["e2e/*"]


@pytest.fixture
def auth_client(client, db):
    """Authenticated test client fixture."""
    User = get_user_model()
    user = User.objects.create_user(username="testuser", password="testpass123")
    client.force_login(user)
    return client


# Shared platform fixtures (platform-context[testing])
try:
    from platform_context.testing.fixtures import (  # noqa: F401
        htmx_client,
    )
except ImportError:
    pass
