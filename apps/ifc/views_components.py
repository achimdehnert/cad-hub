"""
IFC Component Views

ListView for Windows, Doors, Walls, Slabs.
"""
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from .models import Door, IFCModel, Slab, Wall, Window
from .views import HtmxMixin


class WindowListView(HtmxMixin, ListView):
    """Fensterliste mit Filterung"""

    model = Window
    template_name = "cad_hub/window_list.html"
    partial_template_name = "cad_hub/partials/_window_table.html"
    context_object_name = "windows"
    paginate_by = 50

    def get_queryset(self):
        model_id = self.kwargs["model_id"]
        qs = Window.objects.filter(ifc_model_id=model_id).select_related("floor", "room")

        if floor_id := self.request.GET.get("floor"):
            qs = qs.filter(floor_id=floor_id)
        if room_id := self.request.GET.get("room"):
            qs = qs.filter(room_id=room_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = get_object_or_404(IFCModel, pk=self.kwargs["model_id"])
        ctx["model"] = model
        ctx["floors"] = model.floors.all()
        ctx["total_count"] = self.get_queryset().count()
        ctx["total_area"] = self.get_queryset().aggregate(Sum("area"))["area__sum"] or 0
        return ctx


class DoorListView(HtmxMixin, ListView):
    """Türliste mit Filterung"""

    model = Door
    template_name = "cad_hub/door_list.html"
    partial_template_name = "cad_hub/partials/_door_table.html"
    context_object_name = "doors"
    paginate_by = 50

    def get_queryset(self):
        model_id = self.kwargs["model_id"]
        qs = Door.objects.filter(ifc_model_id=model_id).select_related(
            "floor", "from_room", "to_room"
        )

        if floor_id := self.request.GET.get("floor"):
            qs = qs.filter(floor_id=floor_id)
        if fire_rating := self.request.GET.get("fire_rating"):
            qs = qs.filter(fire_rating=fire_rating)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = get_object_or_404(IFCModel, pk=self.kwargs["model_id"])
        ctx["model"] = model
        ctx["floors"] = model.floors.all()
        ctx["total_count"] = self.get_queryset().count()
        return ctx


class WallListView(HtmxMixin, ListView):
    """Wandliste mit Filterung"""

    model = Wall
    template_name = "cad_hub/wall_list.html"
    partial_template_name = "cad_hub/partials/_wall_table.html"
    context_object_name = "walls"
    paginate_by = 50

    def get_queryset(self):
        model_id = self.kwargs["model_id"]
        qs = Wall.objects.filter(ifc_model_id=model_id).select_related("floor")

        if floor_id := self.request.GET.get("floor"):
            qs = qs.filter(floor_id=floor_id)
        if wall_type := self.request.GET.get("type"):
            if wall_type == "external":
                qs = qs.filter(is_external=True)
            elif wall_type == "internal":
                qs = qs.filter(is_external=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = get_object_or_404(IFCModel, pk=self.kwargs["model_id"])
        ctx["model"] = model
        ctx["floors"] = model.floors.all()
        ctx["total_count"] = self.get_queryset().count()
        ctx["total_gross_area"] = (
            self.get_queryset().aggregate(Sum("gross_area"))["gross_area__sum"] or 0
        )
        ctx["total_net_area"] = self.get_queryset().aggregate(Sum("net_area"))["net_area__sum"] or 0
        ctx["external_count"] = self.get_queryset().filter(is_external=True).count()
        ctx["internal_count"] = self.get_queryset().filter(is_external=False).count()
        return ctx


class SlabListView(HtmxMixin, ListView):
    """Deckenliste mit Filterung"""

    model = Slab
    template_name = "cad_hub/slab_list.html"
    partial_template_name = "cad_hub/partials/_slab_table.html"
    context_object_name = "slabs"
    paginate_by = 50

    def get_queryset(self):
        model_id = self.kwargs["model_id"]
        qs = Slab.objects.filter(ifc_model_id=model_id).select_related("floor")

        if floor_id := self.request.GET.get("floor"):
            qs = qs.filter(floor_id=floor_id)
        if slab_type := self.request.GET.get("slab_type"):
            qs = qs.filter(slab_type=slab_type)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = get_object_or_404(IFCModel, pk=self.kwargs["model_id"])
        ctx["model"] = model
        ctx["floors"] = model.floors.all()
        ctx["total_count"] = self.get_queryset().count()
        ctx["total_area"] = self.get_queryset().aggregate(Sum("area"))["area__sum"] or 0
        ctx["total_volume"] = self.get_queryset().aggregate(Sum("volume"))["volume__sum"] or 0
        return ctx
