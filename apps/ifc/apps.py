"""IFC app configuration."""
from django.apps import AppConfig


class IfcConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ifc"
    verbose_name = "IFC"
