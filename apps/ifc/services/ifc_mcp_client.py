# apps/cad_hub/services/ifc_mcp_client.py
"""
IFC MCP Client - Kommuniziert mit IFC MCP Backend

Alle Business Logic läuft im IFC MCP Backend.
cad_hub ist PURE Frontend.
"""

from typing import Any

import httpx
from django.conf import settings


class IfcMcpClient:
    """Client für IFC MCP Backend API"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or getattr(settings, "IFC_MCP_URL", "http://localhost:8001")  # noqa: S104
        self.timeout = 30.0

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Generic HTTP request"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}{endpoint}"
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()

            # Return JSON or raw content
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return {"content": response.content}

    # ========== Projects ==========

    async def list_projects(self) -> list[dict[str, Any]]:
        """Liste alle Projekte"""
        return await self._request("GET", "/api/projects")

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Projekt Details"""
        return await self._request("GET", f"/api/projects/{project_id}")

    async def import_ifc(self, file_path: str) -> dict[str, Any]:
        """IFC-Datei importieren"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            return await self._request("POST", "/api/projects/import", files=files)

    async def delete_project(self, project_id: str) -> dict[str, Any]:
        """Projekt löschen"""
        return await self._request("DELETE", f"/api/projects/{project_id}")

    # ========== German Standards ==========

    async def calculate_din277(
        self, project_id: str, bgf: float | None = None, floor_height: float = 3.0
    ) -> dict[str, Any]:
        """DIN 277 Flächenberechnung"""
        data = {"project_id": project_id, "bgf": bgf, "floor_height": floor_height}
        return await self._request("POST", "/api/din277/calculate", json=data)

    async def calculate_woflv(self, project_id: str, default_hoehe: float = 2.5) -> dict[str, Any]:
        """WoFlV Wohnflächenberechnung"""
        data = {"project_id": project_id, "default_hoehe": default_hoehe}
        return await self._request("POST", "/api/woflv/calculate", json=data)

    async def generate_gaeb(
        self, project_id: str, projekt_nummer: str = "", format: str = "xml"
    ) -> bytes:
        """GAEB Leistungsverzeichnis generieren"""
        data = {"project_id": project_id, "projekt_nummer": projekt_nummer, "format": format}
        result = await self._request("POST", "/api/gaeb/generate", json=data)
        return result.get("content", b"")

    # ========== Schedules ==========

    async def get_window_schedule(
        self, project_id: str, storey_id: str | None = None
    ) -> dict[str, Any]:
        """Fenster-Liste"""
        params = {"storey_id": storey_id} if storey_id else {}
        return await self._request(
            "POST", f"/api/projects/{project_id}/schedules/windows", params=params
        )

    async def get_door_schedule(
        self, project_id: str, storey_id: str | None = None
    ) -> dict[str, Any]:
        """Türen-Liste"""
        params = {"storey_id": storey_id} if storey_id else {}
        return await self._request(
            "POST", f"/api/projects/{project_id}/schedules/doors", params=params
        )

    async def get_wall_schedule(
        self, project_id: str, storey_id: str | None = None
    ) -> dict[str, Any]:
        """Wand-Liste"""
        params = {"storey_id": storey_id} if storey_id else {}
        return await self._request(
            "POST", f"/api/projects/{project_id}/schedules/walls", params=params
        )

    # ========== Ex-Protection (ATEX) ==========

    async def analyze_ex_zones(self, project_id: str) -> dict[str, Any]:
        """ATEX Explosionsschutz-Analyse"""
        return await self._request("GET", f"/api/projects/{project_id}/ex-zones")

    async def analyze_fire_rating(self, project_id: str) -> dict[str, Any]:
        """Brandschutz-Analyse"""
        return await self._request("GET", f"/api/projects/{project_id}/fire-rating")

    async def get_room_volumes(self, project_id: str) -> dict[str, Any]:
        """Raumvolumen für Ex-Schutz"""
        return await self._request("GET", f"/api/projects/{project_id}/room-volumes")
