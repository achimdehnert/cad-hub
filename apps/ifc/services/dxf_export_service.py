"""
DXF Export Service (Issue #2).

Converts IFC model data (walls, rooms, doors, windows, slabs) to DXF
with configurable layer selection. Output in AutoCAD 2018 format.
"""

import io
import logging
from dataclasses import dataclass

import ezdxf

from ..models import Door, IFCModel, Room, Slab, Wall, Window

logger = logging.getLogger(__name__)


@dataclass
class DXFExportLayer:
    """Represents an exportable layer with metadata."""

    key: str
    name: str
    description: str
    color: int
    entity_count: int = 0


# Available export layers
EXPORT_LAYERS = {
    "walls_external": DXFExportLayer(
        key="walls_external",
        name="A-WALL-EXT",
        description="Außenwände",
        color=1,  # Red
    ),
    "walls_internal": DXFExportLayer(
        key="walls_internal",
        name="A-WALL-INT",
        description="Innenwände",
        color=3,  # Green
    ),
    "rooms": DXFExportLayer(
        key="rooms",
        name="A-ROOM",
        description="Räume (Umriss + Nummer)",
        color=5,  # Blue
    ),
    "doors": DXFExportLayer(
        key="doors",
        name="A-DOOR",
        description="Türen",
        color=6,  # Magenta
    ),
    "windows": DXFExportLayer(
        key="windows",
        name="A-WINDOW",
        description="Fenster",
        color=4,  # Cyan
    ),
    "slabs": DXFExportLayer(
        key="slabs",
        name="A-SLAB",
        description="Decken / Bodenplatten",
        color=8,  # Gray
    ),
    "dimensions": DXFExportLayer(
        key="dimensions",
        name="A-DIMS",
        description="Bemaßung (Wandlängen)",
        color=7,  # White/Black
    ),
    "text": DXFExportLayer(
        key="text",
        name="A-TEXT",
        description="Raumnummern & Beschriftung",
        color=2,  # Yellow
    ),
}


def get_available_layers(ifc_model: IFCModel) -> list[DXFExportLayer]:
    """Get available layers with entity counts for a given IFC model."""
    layers = []

    ext_walls = ifc_model.walls.filter(is_external=True).count()
    int_walls = ifc_model.walls.filter(is_external=False).count()
    rooms = ifc_model.rooms.count()
    doors = ifc_model.doors.count()
    windows = ifc_model.windows.count()
    slabs = ifc_model.slabs.count()

    counts = {
        "walls_external": ext_walls,
        "walls_internal": int_walls,
        "rooms": rooms,
        "doors": doors,
        "windows": windows,
        "slabs": slabs,
        "dimensions": ext_walls + int_walls,
        "text": rooms,
    }

    for key, layer in EXPORT_LAYERS.items():
        layer_copy = DXFExportLayer(
            key=layer.key,
            name=layer.name,
            description=layer.description,
            color=layer.color,
            entity_count=counts.get(key, 0),
        )
        layers.append(layer_copy)

    return layers


def export_ifc_to_dxf(
    ifc_model: IFCModel,
    selected_layers: list[str],
    floor_id: str | None = None,
) -> io.BytesIO:
    """Export IFC model data as DXF file.

    Args:
        ifc_model: The IFC model to export.
        selected_layers: List of layer keys to include (e.g. ['walls_external', 'rooms']).
        floor_id: Optional floor PK to filter export to a single floor.

    Returns:
        BytesIO buffer containing the DXF file content.
    """
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    # Set units to meters
    doc.header["$INSUNITS"] = 6  # Meters
    doc.header["$MEASUREMENT"] = 1  # Metric

    # Create layers
    for key in selected_layers:
        if key in EXPORT_LAYERS:
            layer_def = EXPORT_LAYERS[key]
            doc.layers.add(layer_def.name, color=layer_def.color)

    # Base queryset filter
    floor_filter = {}
    if floor_id:
        floor_filter["floor_id"] = floor_id

    # Y offset per floor for stacked export (when no floor filter)
    floor_offsets = {}
    if not floor_id:
        floors = ifc_model.floors.order_by("sort_order")
        for idx, floor in enumerate(floors):
            floor_offsets[floor.pk] = idx * 50.0  # 50m spacing between floors
    else:
        floor_offsets[floor_id] = 0.0

    # --- Export Walls ---
    if "walls_external" in selected_layers:
        _export_walls(
            msp,
            ifc_model,
            floor_filter,
            floor_offsets,
            is_external=True,
            layer_name="A-WALL-EXT",
        )

    if "walls_internal" in selected_layers:
        _export_walls(
            msp,
            ifc_model,
            floor_filter,
            floor_offsets,
            is_external=False,
            layer_name="A-WALL-INT",
        )

    # --- Export Rooms ---
    if "rooms" in selected_layers:
        _export_rooms(msp, ifc_model, floor_filter, floor_offsets)

    # --- Export Doors ---
    if "doors" in selected_layers:
        _export_doors(msp, ifc_model, floor_filter, floor_offsets)

    # --- Export Windows ---
    if "windows" in selected_layers:
        _export_windows(msp, ifc_model, floor_filter, floor_offsets)

    # --- Export Slabs ---
    if "slabs" in selected_layers:
        _export_slabs(msp, ifc_model, floor_filter, floor_offsets)

    # --- Export Dimensions ---
    if "dimensions" in selected_layers:
        _export_dimensions(msp, ifc_model, floor_filter, floor_offsets)

    # --- Export Text ---
    if "text" in selected_layers:
        _export_text(msp, ifc_model, floor_filter, floor_offsets)

    # Write to buffer
    output = io.BytesIO()
    doc.write(output)
    output.seek(0)

    logger.info(
        "DXF export: model=%s, layers=%s, floor=%s",
        ifc_model.pk,
        selected_layers,
        floor_id,
    )

    return output


def _get_y_offset(floor_pk, floor_offsets: dict) -> float:
    """Get Y offset for a floor."""
    if floor_pk and floor_pk in floor_offsets:
        return floor_offsets[floor_pk]
    return 0.0


def _export_walls(msp, ifc_model, floor_filter, floor_offsets, is_external, layer_name):
    """Export walls as rectangles (length x width)."""
    walls = Wall.objects.filter(
        ifc_model=ifc_model, is_external=is_external, **floor_filter
    ).select_related("floor")

    x_offset = 0.0
    for wall in walls:
        y_off = _get_y_offset(wall.floor_id, floor_offsets)
        length = float(wall.length or 1.0)
        thickness = float(wall.width or 0.2)

        # Draw wall as rectangle
        points = [
            (x_offset, y_off),
            (x_offset + length, y_off),
            (x_offset + length, y_off + thickness),
            (x_offset, y_off + thickness),
            (x_offset, y_off),
        ]
        msp.add_lwpolyline(points, dxfattribs={"layer": layer_name})
        x_offset += length + 0.5


def _export_rooms(msp, ifc_model, floor_filter, floor_offsets):
    """Export rooms as rectangles with area label."""
    rooms = Room.objects.filter(ifc_model=ifc_model, **floor_filter).select_related("floor")

    x_offset = 0.0
    for room in rooms:
        y_off = _get_y_offset(room.floor_id, floor_offsets)
        area = float(room.area or 10.0)
        # Approximate square room for visualization
        side = area**0.5
        points = [
            (x_offset, y_off),
            (x_offset + side, y_off),
            (x_offset + side, y_off + side),
            (x_offset, y_off + side),
            (x_offset, y_off),
        ]
        msp.add_lwpolyline(points, dxfattribs={"layer": "A-ROOM"})
        x_offset += side + 1.0


def _export_doors(msp, ifc_model, floor_filter, floor_offsets):
    """Export doors as arc symbols."""
    doors = Door.objects.filter(ifc_model=ifc_model, **floor_filter).select_related("floor")

    x_offset = 0.0
    for door in doors:
        y_off = _get_y_offset(door.floor_id, floor_offsets)
        width = float(door.width or 0.9)
        # Door symbol: line + arc
        msp.add_line(
            (x_offset, y_off),
            (x_offset, y_off + width),
            dxfattribs={"layer": "A-DOOR"},
        )
        msp.add_arc(
            center=(x_offset, y_off),
            radius=width,
            start_angle=0,
            end_angle=90,
            dxfattribs={"layer": "A-DOOR"},
        )
        x_offset += width + 0.5


def _export_windows(msp, ifc_model, floor_filter, floor_offsets):
    """Export windows as triple-line symbols."""
    windows = Window.objects.filter(ifc_model=ifc_model, **floor_filter).select_related("floor")

    x_offset = 0.0
    for window in windows:
        y_off = _get_y_offset(window.floor_id, floor_offsets)
        width = float(window.width or 1.2)
        # Window symbol: 3 parallel lines
        for i in range(3):
            offset_y = y_off + i * 0.05
            msp.add_line(
                (x_offset, offset_y),
                (x_offset + width, offset_y),
                dxfattribs={"layer": "A-WINDOW"},
            )
        x_offset += width + 0.5


def _export_slabs(msp, ifc_model, floor_filter, floor_offsets):
    """Export slabs as hatched rectangles."""
    slabs = Slab.objects.filter(ifc_model=ifc_model, **floor_filter).select_related("floor")

    x_offset = 0.0
    for slab in slabs:
        y_off = _get_y_offset(slab.floor_id, floor_offsets)
        area = float(slab.area or 20.0)
        side = area**0.5
        points = [
            (x_offset, y_off),
            (x_offset + side, y_off),
            (x_offset + side, y_off + side),
            (x_offset, y_off + side),
            (x_offset, y_off),
        ]
        msp.add_lwpolyline(points, dxfattribs={"layer": "A-SLAB"})
        x_offset += side + 1.0


def _export_dimensions(msp, ifc_model, floor_filter, floor_offsets):
    """Export wall length dimensions."""
    walls = Wall.objects.filter(ifc_model=ifc_model, **floor_filter).select_related("floor")

    x_offset = 0.0
    for wall in walls:
        y_off = _get_y_offset(wall.floor_id, floor_offsets)
        length = float(wall.length or 1.0)
        # Add dimension text
        dim_text = f"{length:.2f}m"
        msp.add_text(
            dim_text,
            height=0.15,
            dxfattribs={
                "layer": "A-DIMS",
                "insert": (x_offset + length / 2, y_off - 0.5),
            },
        )
        x_offset += length + 0.5


def _export_text(msp, ifc_model, floor_filter, floor_offsets):
    """Export room numbers and names as text."""
    rooms = Room.objects.filter(ifc_model=ifc_model, **floor_filter).select_related("floor")

    x_offset = 0.0
    for room in rooms:
        y_off = _get_y_offset(room.floor_id, floor_offsets)
        area = float(room.area or 10.0)
        side = area**0.5
        # Room number
        msp.add_text(
            room.number,
            height=0.3,
            dxfattribs={
                "layer": "A-TEXT",
                "insert": (x_offset + side / 2, y_off + side / 2),
            },
        )
        # Area text below number
        msp.add_text(
            f"{area:.1f} m²",
            height=0.2,
            dxfattribs={
                "layer": "A-TEXT",
                "insert": (x_offset + side / 2, y_off + side / 2 - 0.4),
            },
        )
        x_offset += side + 1.0
