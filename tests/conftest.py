# tests/conftest.py — ADR-058 §Confirmation
import pytest

# Shared platform fixtures (platform-context[testing])
from platform_context.testing.fixtures import (  # noqa: F401
    admin_client,
    admin_user,
    auth_client,
    htmx_client,
)

# Repo-specific: user via UserFactory (cad-hub uses standard Django User)
@pytest.fixture
def user(db):
    """Standard authenticated user."""
    from tests.factories import UserFactory
    return UserFactory()
