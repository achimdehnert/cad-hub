"""DXF app configuration."""
from django.apps import AppConfig


class DxfConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dxf"
    verbose_name = "DXF/DWG"
