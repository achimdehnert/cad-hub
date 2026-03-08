"""Tests for registry models: NL2CADModule, ModulePricing, BerufsProfil, TenantSubscription, DiscountRule."""
import pytest
from decimal import Decimal


@pytest.fixture
def module(db):
    from apps.registry.models import NL2CADModule, ModuleStatus
    return NL2CADModule.objects.create(
        id="brandschutz",
        package="nl2cad-brandschutz",
        name="Brandschutz",
        status=ModuleStatus.STABLE,
    )


@pytest.fixture
def profil(db, module):
    from apps.registry.models import BerufsProfil
    p = BerufsProfil.objects.create(
        id="brandschutz_sv",
        name="Brandschutz-Sachverständiger",
        icon="🔥",
        nlp_keywords="brandschutz,fluchtweg,rauchmelder",
    )
    return p


class TestNL2CADModule:
    def test_should_create_with_defaults(self, module):
        assert module.id == "brandschutz"
        assert module.package == "nl2cad-brandschutz"
        assert module.is_required is False
        assert module.features == []
        assert module.deps == []

    def test_should_str_include_package_and_status(self, module):
        s = str(module)
        assert "nl2cad-brandschutz" in s
        assert "Stabil" in s

    def test_should_filter_by_status(self, db, module):
        from apps.registry.models import NL2CADModule, ModuleStatus
        NL2CADModule.objects.create(
            id="gaeb", package="nl2cad-gaeb", name="GAEB",
            status=ModuleStatus.PLANNED,
        )
        stable = NL2CADModule.objects.filter(status=ModuleStatus.STABLE)
        planned = NL2CADModule.objects.filter(status=ModuleStatus.PLANNED)
        assert stable.count() == 1
        assert planned.count() == 1

    def test_should_store_json_fields(self, db):
        from apps.registry.models import NL2CADModule, ModuleStatus
        m = NL2CADModule.objects.create(
            id="areas",
            package="nl2cad-areas",
            name="Flächen",
            status=ModuleStatus.STABLE,
            features=["DIN 277", "WoFlV"],
            deps=["nl2cad-core"],
            norms=["DIN 277 (2016)"],
        )
        assert "DIN 277" in m.features
        assert "nl2cad-core" in m.deps

    def test_should_return_none_for_standard_pricing_when_missing(self, module):
        assert module.standard_pricing is None


class TestModulePricing:
    def test_should_auto_generate_label_free(self, db, module):
        from apps.registry.models import ModulePricing
        pricing = ModulePricing.objects.create(
            module=module,
            setup_eur=Decimal("0"),
            monthly_eur=Decimal("0"),
        )
        assert "Inklusive" in pricing.label

    def test_should_auto_generate_label_monthly_only(self, db, module):
        from apps.registry.models import ModulePricing
        pricing = ModulePricing.objects.create(
            module=module,
            setup_eur=Decimal("0"),
            monthly_eur=Decimal("79"),
        )
        assert "79" in pricing.label
        assert "Monat" in pricing.label

    def test_should_auto_generate_label_with_setup(self, db, module):
        from apps.registry.models import ModulePricing
        pricing = ModulePricing.objects.create(
            module=module,
            setup_eur=Decimal("500"),
            monthly_eur=Decimal("49"),
        )
        assert "Setup" in pricing.label
        assert "500" in pricing.label

    def test_should_use_custom_label_when_provided(self, db, module):
        from apps.registry.models import ModulePricing
        pricing = ModulePricing.objects.create(
            module=module,
            monthly_eur=Decimal("99"),
            label="Spezialtarif",
        )
        assert pricing.label == "Spezialtarif"

    def test_should_be_standard_pricing_for_module(self, db, module):
        from apps.registry.models import ModulePricing
        ModulePricing.objects.create(
            module=module,
            monthly_eur=Decimal("59"),
        )
        assert module.standard_pricing is not None
        assert module.standard_pricing.monthly_eur == Decimal("59")


class TestBerufsProfil:
    def test_should_create(self, profil):
        assert profil.id == "brandschutz_sv"
        assert profil.icon == "🔥"

    def test_should_str_include_name(self, profil):
        assert "Brandschutz-Sachverständiger" in str(profil)

    def test_should_parse_nlp_keywords_list(self, profil):
        kws = profil.nlp_keywords_list
        assert "brandschutz" in kws
        assert "fluchtweg" in kws
        assert "rauchmelder" in kws

    def test_should_return_empty_list_for_no_keywords(self, db):
        from apps.registry.models import BerufsProfil
        p = BerufsProfil.objects.create(id="empty", name="Leer", nlp_keywords="")
        assert p.nlp_keywords_list == []


class TestDiscountRule:
    def test_should_create(self, db):
        from apps.registry.models import DiscountRule
        rule = DiscountRule.objects.create(
            name="3-Modul-Rabatt",
            min_modules=3,
            discount_percent=Decimal("15"),
        )
        assert rule.is_active is True
        assert str(rule) == "15% ab 3 Modulen"

    def test_should_order_by_min_modules(self, db):
        from apps.registry.models import DiscountRule
        DiscountRule.objects.create(name="5er", min_modules=5, discount_percent=Decimal("20"))
        DiscountRule.objects.create(name="2er", min_modules=2, discount_percent=Decimal("10"))
        rules = list(DiscountRule.objects.all())
        assert rules[0].min_modules <= rules[1].min_modules


class TestTenantSubscription:
    def test_should_create_pending(self, db, module):
        from apps.registry.models import TenantSubscription
        import uuid
        tid = uuid.uuid4()

        # Need an Organization — use django_tenancy
        from django_tenancy.models import Organization
        org = Organization.objects.create(name="Test Org", slug="test-org")

        sub = TenantSubscription.objects.create(
            tenant_id=tid,
            organization=org,
            module=module,
            monthly_eur=Decimal("79"),
        )
        assert sub.status == "pending"
        assert sub.monthly_revenue == Decimal("0")  # not active yet

    def test_should_return_revenue_when_active(self, db, module):
        from apps.registry.models import TenantSubscription
        import uuid
        from django_tenancy.models import Organization
        org = Organization.objects.create(name="Active Org", slug="active-org")
        sub = TenantSubscription.objects.create(
            tenant_id=uuid.uuid4(),
            organization=org,
            module=module,
            status=TenantSubscription.SubscriptionStatus.ACTIVE,
            monthly_eur=Decimal("99"),
        )
        assert sub.monthly_revenue == Decimal("99")
