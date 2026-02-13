"""Root URL configuration for CAD Hub."""
from django.contrib import admin
from django.urls import include, path

from apps.core.healthz import liveness, readiness

from . import views

urlpatterns = [
    # Health endpoints (no auth, no tenant)
    path("livez/", liveness, name="health-liveness"),
    path("healthz/", readiness, name="health-readiness"),
    path("health/", liveness, name="health-compat"),

    # Public pages
    path("", views.landing, name="landing"),
    path("login/", views.login_view, name="login"),

    # Admin
    path("admin/", admin.site.urls),

    # App URLs
    path("ifc/", include("apps.ifc.urls", namespace="ifc")),
    path("dxf/", include("apps.dxf.urls", namespace="dxf")),
    path("areas/", include("apps.areas.urls", namespace="areas")),
    path("brandschutz/", include("apps.brandschutz.urls", namespace="brandschutz")),
    path("avb/", include("apps.avb.urls", namespace="avb")),
    path("export/", include("apps.export.urls", namespace="export")),
]
