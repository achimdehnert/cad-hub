"""Regression tests for the tenant membership guard (security).

The vendored SubdomainTenantMiddleware resolved tenants from the
subdomain / ``X-Tenant-ID`` header without a membership check, so an
authenticated user could enter a foreign org's context (IDOR). The
guard must reject tenants the user is not a member of.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django_tenancy.middleware import SubdomainTenantMiddleware
from django_tenancy.models import Membership, Organization

User = get_user_model()


@pytest.fixture(autouse=True)
def _allow_test_hosts(settings):
    settings.ALLOWED_HOSTS = ["acme.example.com", "example.com"]


def _run(request):
    SubdomainTenantMiddleware(get_response=lambda r: r).process_request(request)
    return request


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme", slug="acme", status="active")


@pytest.fixture
def member(db, org):
    user = User.objects.create_user(username="member", password="p")
    Membership.objects.create(tenant_id=org.tenant_id, organization=org, user=user)
    return user


@pytest.fixture
def outsider(db):
    return User.objects.create_user(username="outsider", password="p")


@pytest.mark.django_db
def test_should_honour_subdomain_for_member(org, member):
    request = RequestFactory().get("/", HTTP_HOST="acme.example.com")
    request.user = member
    _run(request)
    assert request.tenant_id == org.tenant_id


@pytest.mark.django_db
def test_should_reject_subdomain_for_non_member(org, outsider):
    request = RequestFactory().get("/", HTTP_HOST="acme.example.com")
    request.user = outsider
    _run(request)
    assert request.tenant_id is None


@pytest.mark.django_db
def test_should_reject_header_for_non_member(org, outsider):
    request = RequestFactory().get(
        "/", HTTP_HOST="example.com", HTTP_X_TENANT_ID=str(org.tenant_id)
    )
    request.user = outsider
    _run(request)
    assert request.tenant_id is None


@pytest.mark.django_db
def test_should_allow_anonymous_subdomain_resolution(org):
    request = RequestFactory().get("/", HTTP_HOST="acme.example.com")
    request.user = AnonymousUser()
    _run(request)
    assert request.tenant_id == org.tenant_id
