"""Areas app configuration."""

from django.apps import AppConfig


class AreasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.areas"
    verbose_name = "Flächen (DIN 277 / WoFlV)"
