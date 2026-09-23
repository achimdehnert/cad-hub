"""Vorgang app configuration."""

from django.apps import AppConfig


class VorgangConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vorgang"
    verbose_name = "Vorgang"
