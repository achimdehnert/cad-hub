"""
IFC Query Service Layer (ADR-041).

Encapsulates ORM queries for IFC views.
"""

from django.db.models import Count, Sum

from ..models import Door, Floor, IFCModel, IFCProject, Room, Slab, Wall, Window


def get_dashboard_stats(tenant_id: str | None) -> dict:
    """Dashboard statistics for a tenant."""
    if not tenant_id:
        return {"projects": 0, "models": 0, "rooms": 0}
    return {
        "projects": IFCProject.objects.filter(tenant_id=tenant_id).count(),
        "models": IFCModel.objects.filter(tenant_id=tenant_id, status="ready").count(),
        "rooms": Room.objects.filter(tenant_id=tenant_id).count(),
    }


def get_recent_projects(tenant_id: str | None, limit: int = 5):
    """Recent projects for a tenant."""
    if not tenant_id:
        return IFCProject.objects.none()
    return IFCProject.objects.filter(tenant_id=tenant_id)[:limit]


def get_model_floor_stats(model: IFCModel):
    """Floors with room count annotations for a model."""
    return model.floors.annotate(room_count=Count("rooms")).order_by("sort_order")


def get_model_content_stats(model: IFCModel) -> dict:
    """Aggregated content statistics for IFC content overview."""
    return {
        "floors": model.floors.count(),
        "rooms": model.rooms.count(),
        "windows": model.windows.count(),
        "doors": model.doors.count(),
        "walls": model.walls.count(),
        "slabs": model.slabs.count(),
        "total_room_area": model.rooms.aggregate(Sum("area"))["area__sum"] or 0,
        "total_wall_gross_area": model.walls.aggregate(Sum("gross_area"))["gross_area__sum"] or 0,
        "total_wall_net_area": model.walls.aggregate(Sum("net_area"))["net_area__sum"] or 0,
        "total_slab_area": model.slabs.aggregate(Sum("area"))["area__sum"] or 0,
        "external_walls": model.walls.filter(is_external=True).count(),
        "internal_walls": model.walls.filter(is_external=False).count(),
    }


def get_floors_with_stats(model: IFCModel) -> list[dict]:
    """Per-floor statistics for content overview."""
    result = []
    for floor in model.floors.all():
        result.append(
            {
                "floor": floor,
                "rooms": floor.rooms.count(),
                "windows": floor.windows.count(),
                "doors": floor.doors.count(),
                "walls": floor.walls.count(),
                "slabs": floor.slabs.count(),
                "room_area": floor.rooms.aggregate(Sum("area"))["area__sum"] or 0,
            }
        )
    return result


def get_next_version(project: IFCProject) -> int:
    """Next version number for a new model in a project."""
    last = IFCModel.objects.filter(project=project).order_by("-version").first()
    return (last.version + 1) if last else 1


def get_area_summary(ifc_model: IFCModel) -> dict:
    """DIN 277 area summary from rooms."""
    rooms = Room.objects.filter(ifc_model=ifc_model)
    total_area = rooms.aggregate(Sum("area"))["area__sum"] or 0
    return {
        "areas": {
            "bgf": total_area,
            "ngf": total_area * 0.85,
            "nf": total_area * 0.75,
            "tf": total_area * 0.10,
            "vf": total_area * 0.05,
        },
        "din277": {
            "total_area": total_area,
            "rooms_count": rooms.count(),
        },
    }


def get_rooms_queryset(model_id, floor_id=None, usage=None, search=None):
    """Filtered Room queryset for list view."""
    qs = Room.objects.filter(ifc_model_id=model_id)
    if floor_id:
        qs = qs.filter(floor_id=floor_id)
    if usage:
        qs = qs.filter(usage_category=usage)
    if search:
        qs = qs.filter(name__icontains=search)
    return qs.select_related("floor").order_by("number")


def get_floors_for_model(model_id):
    """Floor queryset for a model."""
    return Floor.objects.filter(ifc_model_id=model_id)


def extract_ifc_data(ifc_model: IFCModel) -> dict:
    """Extract all IFC data from DB for export views."""
    rooms_qs = list(
        Room.objects.filter(ifc_model=ifc_model).values(
            "name", "number", "area", "perimeter", "height", "volume"
        )
    )
    rooms = [{**r, "area_m2": r["area"]} for r in rooms_qs]

    walls = list(
        Wall.objects.filter(ifc_model=ifc_model).values(
            "name", "ifc_guid", "length", "height", "thickness"
        )
    )
    for wall in walls:
        wall["area"] = (wall.get("length", 0) or 0) * (wall.get("height", 0) or 0)

    doors = list(
        Door.objects.filter(ifc_model=ifc_model).values("name", "ifc_guid", "width", "height")
    )
    for door in doors:
        door["type"] = "Standard"
        if "brand" in (door.get("name", "") or "").lower():
            door["type"] = "Brandschutz"

    windows = list(
        Window.objects.filter(ifc_model=ifc_model).values("name", "ifc_guid", "width", "height")
    )

    slabs = list(
        Slab.objects.filter(ifc_model=ifc_model).values("name", "ifc_guid", "area", "thickness")
    )

    return {
        "rooms": rooms,
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "slabs": slabs,
    }
