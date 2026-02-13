"""AVB app configuration."""
from django.apps import AppConfig


class AvbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.avb"
    verbose_name = "AVB (Ausschreibung/Vergabe)"
