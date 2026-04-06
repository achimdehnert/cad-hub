"""
TenantMixin — filtert alle Queries nach request.tenant_id.

Verwendung in Views:
    class MyView(TenantMixin, ListView):
        ...
    # get_queryset() filtert automatisch nach tenant_id
    # create() setzt tenant_id automatisch
"""

import uuid


class TenantMixin:
    """Mixin für tenant-isolierte Views.

    - get_queryset() filtert nach request.tenant_id
    - form_valid() setzt tenant_id auf neue Objekte
    - _tenant_id() gibt die aktuelle tenant_id zurück
    """

    def _tenant_id(self) -> uuid.UUID:
        return getattr(self.request, "tenant_id", None)

    def get_queryset(self):
        qs = super().get_queryset()
        tid = self._tenant_id()
        if tid:
            return qs.filter(tenant_id=tid)
        return qs

    def form_valid(self, form):
        tid = self._tenant_id()
        if tid and hasattr(form.instance, "tenant_id"):
            form.instance.tenant_id = tid
        return super().form_valid(form)
