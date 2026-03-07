# tests/factories.py — ADR-057 §2.5, ADR-100
import factory

from iil_testkit.factories import UserFactory  # noqa: F401 — re-exported


class CADProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "cad.CADProject"

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"CAD Project {n}")
