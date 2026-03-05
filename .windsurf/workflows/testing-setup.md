---
description: Test-Infrastruktur einrichten (ADR-058)
---

# Testing Setup

## requirements-test.txt
```
pytest>=8.0
pytest-django>=4.8
pytest-mock>=3.12
factory-boy>=3.3
platform-context[testing]>=0.3.0
```

## conftest.py
```python
from platform_context.testing.fixtures import admin_client, admin_user, auth_client, htmx_client  # noqa

@pytest.fixture
def user(db):
    from tests.factories import UserFactory
    return UserFactory()
```

CI: `push → [pytest grün] → [Build] → [Deploy]`
