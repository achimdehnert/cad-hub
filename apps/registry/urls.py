"""Registry URL patterns."""

from django.urls import path

from .views import ModuleListView, ProfileListView, RegistryConfigView

app_name = "registry"

urlpatterns = [
    path("modules/", ModuleListView.as_view(), name="modules"),
    path("profiles/", ProfileListView.as_view(), name="profiles"),
    path("config/", RegistryConfigView.as_view(), name="config"),
]
