"""Vorgang views — dünn, delegiert an services.py (views → services → models)."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.core.htmx import is_htmx_request
from apps.core.mixins import TenantMixin

from . import services
from .models import Befund, Vorgang


class VorgangListView(LoginRequiredMixin, TenantMixin, ListView):
    """Alle Vorgänge des eigenen Mandanten."""

    model = Vorgang
    template_name = "vorgang/vorgang_list.html"
    context_object_name = "vorgaenge"
    paginate_by = 20


class VorgangCreateView(LoginRequiredMixin, TenantMixin, CreateView):
    """Neuen Vorgang anlegen — Speichern läuft über services.lege_vorgang_an."""

    model = Vorgang
    template_name = "vorgang/vorgang_form.html"
    fields = ["art", "titel", "eingereicht_von_rolle", "loeschfrist_am"]

    def form_valid(self, form):
        try:
            vorgang = services.lege_vorgang_an(
                tenant_id=self._tenant_id(),
                user=self.request.user,
                art=form.cleaned_data["art"],
                titel=form.cleaned_data["titel"],
                rolle=form.cleaned_data["eingereicht_von_rolle"],
                loeschfrist_am=form.cleaned_data.get("loeschfrist_am"),
            )
        except ValueError as exc:
            form.add_error("loeschfrist_am", str(exc))
            return self.form_invalid(form)

        self.object = vorgang
        return redirect("vorgang:vorgang_detail", pk=vorgang.pk)


class VorgangDetailView(LoginRequiredMixin, TenantMixin, DetailView):
    """Vorgang mit Dokumenten + Befunden. HTMX-Requests bekommen nur das Partial."""

    model = Vorgang
    template_name = "vorgang/vorgang_detail.html"
    partial_template_name = "vorgang/_befunde.html"
    context_object_name = "vorgang"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dokumente"] = self.object.dokumente.all()
        ctx["befunde"] = self.object.befunde.all()
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        template = self.partial_template_name if is_htmx_request(request) else self.template_name
        return render(request, template, context)


class DokumentUploadView(LoginRequiredMixin, TenantMixin, View):
    """Nimmt ein PDF-Upload für einen Vorgang entgegen und prüft es ggf. sofort."""

    def post(self, request, pk):
        vorgang = get_object_or_404(Vorgang, pk=pk, tenant_id=self._tenant_id())

        uploaded_file = request.FILES.get("datei")
        if not uploaded_file:
            return HttpResponse("Keine Datei ausgewählt.", status=400)

        try:
            dokument = services.haenge_dokument_an(vorgang, uploaded_file)
        except ValueError as exc:
            return HttpResponse(str(exc), status=400)

        vorlagenart = request.POST.get("vorlagenart", "")
        if vorlagenart == "lageplan" or "lageplan" in dokument.dateiname.lower():
            services.pruefe_lageplan(dokument)

        if is_htmx_request(request):
            context = {
                "vorgang": vorgang,
                "dokumente": vorgang.dokumente.all(),
                "befunde": vorgang.befunde.all(),
            }
            return render(request, "vorgang/_befunde.html", context)

        return redirect("vorgang:vorgang_detail", pk=vorgang.pk)


class BefundStatusView(LoginRequiredMixin, TenantMixin, View):
    """Setzt den Status eines Befunds — HTMX bekommt die aktualisierte Zeile zurück."""

    def post(self, request, pk):
        befund = get_object_or_404(Befund, pk=pk, tenant_id=self._tenant_id())

        status = request.POST.get("status", "")
        gueltige_stati = {wert for wert, _ in Befund._meta.get_field("status").choices}
        if status not in gueltige_stati:
            return HttpResponse("Ungültiger Status.", status=400)

        befund = services.setze_befund_status(befund, status)

        if is_htmx_request(request):
            return render(request, "vorgang/_befund_row.html", {"befund": befund})

        return redirect("vorgang:vorgang_detail", pk=befund.vorgang_id)
