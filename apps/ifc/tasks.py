# apps/ifc/tasks.py
"""
Background Tasks für IFC-Verarbeitung.

Nutzt nl2cad.core.parsers.IFCParser als einzige Parse-Schicht.
Kein eigener Parser, keine duplizierten Dataclasses.
"""
import logging
from decimal import Decimal
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from nl2cad_core.parsers.ifc_parser import IFCParser
from nl2cad_core.exceptions import IFCParseError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_ifc_upload(self, model_id: str):
    """
    Verarbeitet einen IFC-Upload.

    Parse-Schicht: nl2cad.core.parsers.IFCParser -> IFCModel
    Persistenz:    Django ORM (Floor, Room, Wall, Door, Window, Slab)
    """
    from .models import Door, Floor, IFCModel, Room, Slab, Wall, Window

    try:
        ifc_model = IFCModel.objects.get(pk=model_id)
        ifc_model.status = IFCModel.Status.PROCESSING
        ifc_model.save(update_fields=["status"])

        tenant_id = ifc_model.tenant_id
        logger.info("Processing IFC: %s (tenant=%s)", model_id, tenant_id)

        parser = IFCParser()
        try:
            nl2cad_model = parser.parse(Path(ifc_model.ifc_file.path))
        except IFCParseError as e:
            ifc_model.status = IFCModel.Status.ERROR
            ifc_model.error_message = str(e)
            ifc_model.save()
            logger.error("IFC parse error: %s", e)
            return

        # Metadata
        ifc_model.ifc_schema = nl2cad_model.schema
        ifc_model.application = nl2cad_model.building_name or nl2cad_model.project_name

        # Geschosse speichern, floor_guid -> Floor ORM Mapping
        floor_map: dict[str, Floor] = {}
        for idx, nl2_floor in enumerate(nl2cad_model.floors):
            floor = Floor.objects.create(
                tenant_id=tenant_id,
                ifc_model=ifc_model,
                ifc_guid=nl2_floor.ifc_id,
                name=nl2_floor.name,
                code=_generate_floor_code(nl2_floor.elevation_m),
                elevation=nl2_floor.elevation_m,
                sort_order=idx,
            )
            floor_map[nl2_floor.ifc_id] = floor

        # Räume
        for nl2_room in nl2cad_model.rooms:
            floor = floor_map.get(nl2_room.floor_guid)
            Room.objects.create(
                tenant_id=tenant_id,
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=nl2_room.ifc_id,
                number=nl2_room.number,
                name=nl2_room.name,
                long_name=nl2_room.long_name,
                area=nl2_room.area_m2,
                height=nl2_room.height_m,
                volume=nl2_room.volume_m3,
                perimeter=nl2_room.perimeter_m,
                usage_category=nl2_room.usage_category,
            )

        # Fenster
        for nl2_win in nl2cad_model.windows:
            floor = floor_map.get(nl2_win.floor_guid)
            Window.objects.create(
                tenant_id=tenant_id,
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=nl2_win.ifc_id,
                number=nl2_win.number,
                name=nl2_win.name,
                width=Decimal(str(nl2_win.width_m)) if nl2_win.width_m else None,
                height=Decimal(str(nl2_win.height_m)) if nl2_win.height_m else None,
                area=Decimal(str(nl2_win.area_m2)) if nl2_win.area_m2 else None,
                material=nl2_win.material,
                u_value=(
                    Decimal(str(nl2_win.u_value_wm2k))
                    if nl2_win.u_value_wm2k is not None
                    else None
                ),
                properties=nl2_win.properties,
            )

        # Türen
        for nl2_door in nl2cad_model.doors:
            floor = floor_map.get(nl2_door.floor_guid)
            Door.objects.create(
                tenant_id=tenant_id,
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=nl2_door.ifc_id,
                number=nl2_door.number,
                name=nl2_door.name,
                width=Decimal(str(nl2_door.width_m)) if nl2_door.width_m else None,
                height=Decimal(str(nl2_door.height_m)) if nl2_door.height_m else None,
                door_type=nl2_door.door_type,
                material=nl2_door.material,
                fire_rating=nl2_door.fire_rating,
            )

        # Wände
        for nl2_wall in nl2cad_model.walls:
            floor = floor_map.get(nl2_wall.floor_guid)
            Wall.objects.create(
                tenant_id=tenant_id,
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=nl2_wall.ifc_id,
                name=nl2_wall.name,
                length=Decimal(str(nl2_wall.length_m)) if nl2_wall.length_m else None,
                height=Decimal(str(nl2_wall.height_m)) if nl2_wall.height_m else None,
                width=Decimal(str(nl2_wall.thickness_m)) if nl2_wall.thickness_m else None,
                gross_area=(
                    Decimal(str(nl2_wall.gross_area_m2)) if nl2_wall.gross_area_m2 else None
                ),
                net_area=(
                    Decimal(str(nl2_wall.net_area_m2)) if nl2_wall.net_area_m2 else None
                ),
                volume=Decimal(str(nl2_wall.volume_m3)) if nl2_wall.volume_m3 else None,
                is_external=nl2_wall.is_external,
                is_load_bearing=nl2_wall.is_load_bearing,
                material=nl2_wall.material,
            )

        # Decken/Platten
        for nl2_slab in nl2cad_model.slabs:
            floor = floor_map.get(nl2_slab.floor_guid)
            Slab.objects.create(
                tenant_id=tenant_id,
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=nl2_slab.ifc_id,
                name=nl2_slab.name,
                slab_type=nl2_slab.slab_type,
                area=Decimal(str(nl2_slab.area_m2)) if nl2_slab.area_m2 else None,
                thickness=(
                    Decimal(str(nl2_slab.thickness_m)) if nl2_slab.thickness_m else None
                ),
                volume=Decimal(str(nl2_slab.volume_m3)) if nl2_slab.volume_m3 else None,
                perimeter=(
                    Decimal(str(nl2_slab.perimeter_m)) if nl2_slab.perimeter_m else None
                ),
                material=nl2_slab.material,
            )

        ifc_model.status = IFCModel.Status.READY
        ifc_model.processed_at = timezone.now()
        ifc_model.save()

        logger.info(
            "Processed %s: %d floors, %d rooms, %d windows, %d doors, %d walls, %d slabs",
            model_id,
            len(nl2cad_model.floors),
            len(nl2cad_model.rooms),
            len(nl2cad_model.windows),
            len(nl2cad_model.doors),
            len(nl2cad_model.walls),
            len(nl2cad_model.slabs),
        )

    except IFCModel.DoesNotExist:
        logger.error("Model %s not found", model_id)
    except Exception as e:
        logger.exception("Processing error: %s", e)
        try:
            ifc_model = IFCModel.objects.get(pk=model_id)
            ifc_model.status = IFCModel.Status.ERROR
            ifc_model.error_message = str(e)
            ifc_model.save()
        except Exception:
            pass


def _generate_floor_code(elevation_m: float) -> str:
    """Generiert Geschoss-Code aus Höhe in Metern."""
    if elevation_m < -0.5:
        level = int(abs(elevation_m) / 3) + 1
        return f"{level}.UG"
    elif elevation_m < 0.5:
        return "EG"
    else:
        level = int(elevation_m / 3)
        if level == 0:
            level = 1
        return f"{level}.OG"
