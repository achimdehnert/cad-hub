# tests/conftest.py — ADR-058
import pytest

pytest_plugins = ["iil_testkit.fixtures"]

# Shared platform fixtures (platform-context[testing])
try:
    from platform_context.testing.fixtures import (  # noqa: F401
        htmx_client,
    )
except ImportError:
    pass
