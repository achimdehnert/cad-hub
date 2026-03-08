# tests/conftest.py
import pytest

# Shared platform fixtures (platform-context[testing])
try:
    from platform_context.testing.fixtures import (  # noqa: F401
        htmx_client,
    )
except ImportError:
    pass
