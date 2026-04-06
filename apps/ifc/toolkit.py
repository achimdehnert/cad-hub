"""
CADToolkit — DomainToolkit implementation for cad-hub.

Provides 4 query tools for the ChatAgent:
  1. query_rooms      — Räume nach Nutzungskategorie/Geschoss filtern
  2. query_walls      — Wände (extern/intern, tragende Wände)
  3. query_components — Fenster, Türen, Decken
  4. query_summary    — Aggregierte Statistiken für ein IFC-Modell
"""

from __future__ import annotations

import logging
from typing import Any

from chat_agent.models import AgentContext, ToolResult
from chat_agent.toolkit import DomainToolkit

from .models import Floor, IFCModel, Room
from .models_components import Door, Slab, Wall, Window

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool Schemas (OpenAI format)
# ---------------------------------------------------------------------------

QUERY_ROOMS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "query_rooms",
        "description": (
            "Gibt Räume eines IFC-Modells zurück, optional gefiltert nach "
            "Nutzungskategorie (DIN 277) und/oder Geschoss-Name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "UUID des IFCModel",
                },
                "usage_category": {
                    "type": "string",
                    "description": (
                        "DIN-277-Kategorie, z.B. 'NF1.1', 'NF1.2', 'NF2'. "
                        "Leer lassen für alle Kategorien."
                    ),
                },
                "floor_name": {
                    "type": "string",
                    "description": "Geschoss-Name, z.B. 'EG', '1.OG'. Leer = alle.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximale Anzahl Ergebnisse (default 20).",
                    "default": 20,
                },
            },
            "required": ["model_id"],
        },
    },
}

QUERY_WALLS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "query_walls",
        "description": (
            "Gibt Wände eines IFC-Modells zurück. "
            "Kann nach Außenwand/Innenwand und tragend/nicht-tragend filtern."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "UUID des IFCModel",
                },
                "is_external": {
                    "type": "boolean",
                    "description": "true = nur Außenwände, false = nur Innenwände. Leer = alle.",
                },
                "is_load_bearing": {
                    "type": "boolean",
                    "description": "true = nur tragende Wände. Leer = alle.",
                },
                "floor_name": {
                    "type": "string",
                    "description": "Geschoss-Name filtern. Leer = alle.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximale Anzahl Ergebnisse (default 20).",
                    "default": 20,
                },
            },
            "required": ["model_id"],
        },
    },
}

QUERY_COMPONENTS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "query_components",
        "description": ("Gibt Bauteile (Fenster, Türen oder Decken) eines IFC-Modells zurück."),
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "UUID des IFCModel",
                },
                "component_type": {
                    "type": "string",
                    "enum": ["windows", "doors", "slabs"],
                    "description": "Bauteiltyp: 'windows', 'doors' oder 'slabs'.",
                },
                "floor_name": {
                    "type": "string",
                    "description": "Geschoss-Name filtern. Leer = alle.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximale Anzahl Ergebnisse (default 20).",
                    "default": 20,
                },
            },
            "required": ["model_id", "component_type"],
        },
    },
}

QUERY_SUMMARY_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "query_summary",
        "description": (
            "Gibt aggregierte Statistiken für ein IFC-Modell zurück: "
            "Anzahl Räume, Wände, Fenster, Türen, Decken, Gesamtflächen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "UUID des IFCModel",
                },
            },
            "required": ["model_id"],
        },
    },
}


# ---------------------------------------------------------------------------
# CADToolkit
# ---------------------------------------------------------------------------


class CADToolkit(DomainToolkit):
    """DomainToolkit für cad-hub IFC-Daten.

    Alle Queries filtern automatisch nach tenant_id aus dem AgentContext.
    """

    @property
    def name(self) -> str:
        return "cad"

    @property
    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            QUERY_ROOMS_TOOL,
            QUERY_WALLS_TOOL,
            QUERY_COMPONENTS_TOOL,
            QUERY_SUMMARY_TOOL,
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        ctx: AgentContext,
    ) -> ToolResult:
        handlers = {
            "query_rooms": self._query_rooms,
            "query_walls": self._query_walls,
            "query_components": self._query_components,
            "query_summary": self._query_summary,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}",
            )
        return await handler(arguments, ctx)

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _query_rooms(self, args: dict[str, Any], ctx: AgentContext) -> ToolResult:
        try:
            model_id = args["model_id"]
            limit = int(args.get("limit", 20))

            qs = Room.objects.filter(
                ifc_model_id=model_id,
                tenant_id=ctx.tenant_id,
            )

            if usage := args.get("usage_category"):
                qs = qs.filter(usage_category=usage)

            if floor_name := args.get("floor_name"):
                qs = qs.filter(floor__name__icontains=floor_name)

            rooms = list(
                qs.select_related("floor").values(
                    "ifc_guid",
                    "number",
                    "name",
                    "area",
                    "height",
                    "usage_category",
                    "floor__name",
                )[:limit]
            )

            return ToolResult(
                success=True,
                data={
                    "count": len(rooms),
                    "rooms": rooms,
                    "total_area": sum(float(r["area"]) for r in rooms if r["area"]),
                },
            )
        except Exception as exc:
            logger.exception("query_rooms failed: %s", exc)
            return ToolResult(success=False, error=str(exc))

    async def _query_walls(self, args: dict[str, Any], ctx: AgentContext) -> ToolResult:
        try:
            model_id = args["model_id"]
            limit = int(args.get("limit", 20))

            qs = Wall.objects.filter(
                ifc_model_id=model_id,
                tenant_id=ctx.tenant_id,
            )

            if (is_ext := args.get("is_external")) is not None:
                qs = qs.filter(is_external=bool(is_ext))

            if (is_lb := args.get("is_load_bearing")) is not None:
                qs = qs.filter(is_load_bearing=bool(is_lb))

            if floor_name := args.get("floor_name"):
                qs = qs.filter(floor__name__icontains=floor_name)

            walls = list(
                qs.select_related("floor").values(
                    "ifc_guid",
                    "name",
                    "length",
                    "height",
                    "width",
                    "gross_area",
                    "net_area",
                    "is_external",
                    "is_load_bearing",
                    "material",
                    "floor__name",
                )[:limit]
            )

            return ToolResult(
                success=True,
                data={
                    "count": len(walls),
                    "walls": walls,
                    "total_gross_area": sum(
                        float(w["gross_area"]) for w in walls if w["gross_area"]
                    ),
                },
            )
        except Exception as exc:
            logger.exception("query_walls failed: %s", exc)
            return ToolResult(success=False, error=str(exc))

    async def _query_components(self, args: dict[str, Any], ctx: AgentContext) -> ToolResult:
        try:
            model_id = args["model_id"]
            component_type = args["component_type"]
            limit = int(args.get("limit", 20))
            floor_name = args.get("floor_name")

            model_map = {
                "windows": (
                    Window,
                    [
                        "ifc_guid",
                        "number",
                        "name",
                        "width",
                        "height",
                        "area",
                        "material",
                        "floor__name",
                    ],
                ),
                "doors": (
                    Door,
                    [
                        "ifc_guid",
                        "number",
                        "name",
                        "width",
                        "height",
                        "door_type",
                        "material",
                        "fire_rating",
                        "floor__name",
                    ],
                ),
                "slabs": (
                    Slab,
                    [
                        "ifc_guid",
                        "name",
                        "slab_type",
                        "area",
                        "thickness",
                        "material",
                        "floor__name",
                    ],
                ),
            }

            if component_type not in model_map:
                return ToolResult(
                    success=False,
                    error=f"Unknown component_type: {component_type}",
                )

            ModelClass, fields = model_map[component_type]
            qs = ModelClass.objects.filter(
                ifc_model_id=model_id,
                tenant_id=ctx.tenant_id,
            )

            if floor_name:
                qs = qs.filter(floor__name__icontains=floor_name)

            items = list(qs.select_related("floor").values(*fields)[:limit])

            return ToolResult(
                success=True,
                data={
                    "component_type": component_type,
                    "count": len(items),
                    "items": items,
                },
            )
        except Exception as exc:
            logger.exception("query_components failed: %s", exc)
            return ToolResult(success=False, error=str(exc))

    async def _query_summary(self, args: dict[str, Any], ctx: AgentContext) -> ToolResult:
        try:
            from django.db.models import Sum

            model_id = args["model_id"]
            tid = ctx.tenant_id

            ifc_model = IFCModel.objects.filter(pk=model_id, tenant_id=tid).first()
            if not ifc_model:
                return ToolResult(
                    success=False,
                    error=f"IFCModel {model_id} not found for this tenant",
                )

            rooms_qs = Room.objects.filter(ifc_model_id=model_id, tenant_id=tid)
            walls_qs = Wall.objects.filter(ifc_model_id=model_id, tenant_id=tid)
            windows_qs = Window.objects.filter(ifc_model_id=model_id, tenant_id=tid)
            doors_qs = Door.objects.filter(ifc_model_id=model_id, tenant_id=tid)
            slabs_qs = Slab.objects.filter(ifc_model_id=model_id, tenant_id=tid)
            floors_qs = Floor.objects.filter(ifc_model_id=model_id, tenant_id=tid)

            summary = {
                "model_id": str(model_id),
                "model_name": str(ifc_model),
                "schema": ifc_model.ifc_schema,
                "status": ifc_model.status,
                "floors": floors_qs.count(),
                "rooms": rooms_qs.count(),
                "total_room_area": float(rooms_qs.aggregate(s=Sum("area"))["s"] or 0),
                "walls": walls_qs.count(),
                "external_walls": walls_qs.filter(is_external=True).count(),
                "load_bearing_walls": walls_qs.filter(is_load_bearing=True).count(),
                "total_wall_gross_area": float(walls_qs.aggregate(s=Sum("gross_area"))["s"] or 0),
                "windows": windows_qs.count(),
                "doors": doors_qs.count(),
                "slabs": slabs_qs.count(),
                "total_slab_area": float(slabs_qs.aggregate(s=Sum("area"))["s"] or 0),
            }

            return ToolResult(success=True, data=summary)
        except Exception as exc:
            logger.exception("query_summary failed: %s", exc)
            return ToolResult(success=False, error=str(exc))
