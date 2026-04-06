"""HTMX utilities for cad-hub (ADR-048).

Local copy of platform_context.htmx — kept in sync manually until
platform-context is vendored via requirements.txt.

Provides:
- is_htmx_request(): Portable HTMX detection (no django_htmx dependency)
- HtmxResponseMixin: CBV mixin for partial/full template switching
- HtmxErrorMiddleware: Convert 4xx/5xx into HTMX-safe toast notifications
"""

import json
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse


def is_htmx_request(request: HttpRequest) -> bool:
    """Portable HTMX detection. Works with or without django_htmx."""
    return request.headers.get("HX-Request") == "true"


class HtmxResponseMixin:
    """Mixin for CBVs that return partials for HTMX requests.

    Set ``partial_template_name`` to the HTMX partial template.

    Example::

        class ProjectListView(HtmxResponseMixin, LoginRequiredMixin, ListView):
            model = ConstructionProject
            template_name = "cad_hub/avb/project_list.html"
            partial_template_name = "cad_hub/avb/partials/_project_list.html"
    """

    partial_template_name: str = ""

    def get_template_names(self) -> list[str]:
        if is_htmx_request(self.request):
            if not self.partial_template_name:
                raise ImproperlyConfigured(
                    f"{self.__class__.__name__} requires partial_template_name"
                )
            return [self.partial_template_name]
        return super().get_template_names()


ERROR_MESSAGES: dict[int, str] = {
    400: "Bad request.",
    403: "Permission denied.",
    404: "Resource not found.",
    405: "Method not allowed.",
    409: "Conflict.",
    429: "Too many requests. Please wait.",
    500: "Internal server error. Please try again.",
    502: "Service temporarily unavailable.",
    503: "Service temporarily unavailable.",
}


class HtmxErrorMiddleware:
    """Convert 4xx/5xx into HTMX-safe responses with toast notifications.

    Install AFTER auth middleware::

        MIDDLEWARE = [
            ...
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "apps.core.htmx.HtmxErrorMiddleware",
            ...
        ]
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if not is_htmx_request(request):
            return response

        if response.status_code == 422:
            return response

        if response.status_code >= 400:
            response["HX-Reswap"] = "none"
            response["HX-Trigger"] = json.dumps(
                {
                    "showToast": {
                        "level": "error" if response.status_code >= 500 else "warning",
                        "message": ERROR_MESSAGES.get(response.status_code, "An error occurred."),
                    }
                }
            )

        return response
