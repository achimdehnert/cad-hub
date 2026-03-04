"""Registry app — Modul-Katalog, Berufsprofile, Tenant-Subscriptions."""
from django.apps import AppConfig


class RegistryConfig(AppConfig):
    name = "apps.registry"
    verbose_name = "Modul-Registry"
    default_auto_field = "django.db.models.BigAutoField"
