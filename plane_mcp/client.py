"""Plane API client wrapper for async HTTP operations."""

from __future__ import annotations

import httpx
from typing import Any


class PlaneClient:
    """Async HTTP client for the Plane API.

    Handles authentication, base URL construction, pagination,
    and error handling for all Plane API endpoints.
    """

    def __init__(self, api_key: str, api_url: str, workspace_slug: str):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.workspace_slug = workspace_slug
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            import os
            import re
            from urllib.parse import urlparse
            
            verify_ssl = True
            env_val = os.environ.get("PLANE_SSL_VERIFY")
            if env_val is not None:
                verify_ssl = env_val.lower() in ("true", "1", "yes")
            else:
                try:
                    host = urlparse(self.api_url).hostname or ""
                    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host) or ":" in host:
                        verify_ssl = False
                except Exception:
                    pass

            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
                verify=verify_ssl,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _ws_url(self, path: str) -> str:
        """Build a workspace-scoped URL path."""
        return f"/api/v1/workspaces/{self.workspace_slug}/{path}"

    def _project_url(self, project_id: str, path: str) -> str:
        """Build a project-scoped URL path."""
        return self._ws_url(f"projects/{project_id}/{path}")

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request and return the JSON response."""
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = await self.client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
        )
        response.raise_for_status()

        if response.status_code == 204:
            return {"status": "success", "message": "Resource deleted successfully"}

        return response.json()

    # ──────────────────────────────────────────────
    # Projects
    # ──────────────────────────────────────────────

    async def list_projects(self) -> dict[str, Any]:
        """List all projects in the workspace."""
        return await self._request("GET", self._ws_url("projects/"))

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a project by ID."""
        return await self._request("GET", self._ws_url(f"projects/{project_id}/"))

    async def create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new project."""
        return await self._request("POST", self._ws_url("projects/"), json_data=data)

    async def update_project(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing project."""
        return await self._request(
            "PATCH", self._ws_url(f"projects/{project_id}/"), json_data=data
        )

    async def delete_project(self, project_id: str) -> dict[str, Any]:
        """Delete a project."""
        return await self._request("DELETE", self._ws_url(f"projects/{project_id}/"))

    # ──────────────────────────────────────────────
    # Work Items (Issues)
    # ──────────────────────────────────────────────

    async def list_work_items(
        self,
        project_id: str,
        cursor: str | None = None,
        per_page: int | None = None,
        expand: str | None = None,
        fields: str | None = None,
        order_by: str | None = None,
    ) -> dict[str, Any]:
        """List work items in a project with optional pagination and filtering."""
        params = {
            "cursor": cursor,
            "per_page": per_page,
            "expand": expand,
            "fields": fields,
            "order_by": order_by,
        }
        return await self._request(
            "GET", self._project_url(project_id, "issues/"), params=params
        )

    async def get_work_item(
        self, project_id: str, work_item_id: str
    ) -> dict[str, Any]:
        """Get a specific work item by ID."""
        return await self._request(
            "GET", self._project_url(project_id, f"issues/{work_item_id}/")
        )

    async def create_work_item(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new work item."""
        return await self._request(
            "POST", self._project_url(project_id, "issues/"), json_data=data
        )

    async def update_work_item(
        self, project_id: str, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing work item."""
        return await self._request(
            "PATCH",
            self._project_url(project_id, f"issues/{work_item_id}/"),
            json_data=data,
        )

    async def delete_work_item(
        self, project_id: str, work_item_id: str
    ) -> dict[str, Any]:
        """Delete a work item."""
        return await self._request(
            "DELETE", self._project_url(project_id, f"issues/{work_item_id}/")
        )

    async def search_work_items(
        self,
        search: str | None = None,
        project_id: str | None = None,
        limit: int | None = None,
        workspace_search: bool | None = None,
    ) -> dict[str, Any]:
        """Search work items across workspace or within a project."""
        params: dict[str, Any] = {
            "search": search,
            "project_id": project_id,
            "limit": limit,
            "workspace_search": workspace_search,
        }
        return await self._request(
            "GET", self._ws_url("issues/"), params=params
        )

    # ──────────────────────────────────────────────
    # Work Item Comments
    # ──────────────────────────────────────────────

    async def add_comment(
        self, project_id: str, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a comment to a work item."""
        return await self._request(
            "POST",
            self._project_url(project_id, f"issues/{work_item_id}/comments/"),
            json_data=data,
        )

    async def list_comments(
        self, project_id: str, work_item_id: str
    ) -> dict[str, Any]:
        """List comments on a work item."""
        return await self._request(
            "GET",
            self._project_url(project_id, f"issues/{work_item_id}/comments/"),
        )

    # ──────────────────────────────────────────────
    # States
    # ──────────────────────────────────────────────

    async def list_states(self, project_id: str) -> dict[str, Any]:
        """List all states for a project."""
        return await self._request(
            "GET", self._project_url(project_id, "states/")
        )

    async def create_state(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new state."""
        return await self._request(
            "POST", self._project_url(project_id, "states/"), json_data=data
        )

    async def get_state(self, project_id: str, state_id: str) -> dict[str, Any]:
        """Get a state by ID."""
        return await self._request(
            "GET", self._project_url(project_id, f"states/{state_id}/")
        )

    # ──────────────────────────────────────────────
    # Labels
    # ──────────────────────────────────────────────

    async def list_labels(self, project_id: str) -> dict[str, Any]:
        """List all labels for a project."""
        return await self._request(
            "GET", self._project_url(project_id, "labels/")
        )

    async def create_label(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new label."""
        return await self._request(
            "POST", self._project_url(project_id, "labels/"), json_data=data
        )

    async def get_label(self, project_id: str, label_id: str) -> dict[str, Any]:
        """Get a label by ID."""
        return await self._request(
            "GET", self._project_url(project_id, f"labels/{label_id}/")
        )

    # ──────────────────────────────────────────────
    # Cycles
    # ──────────────────────────────────────────────

    async def list_cycles(self, project_id: str) -> dict[str, Any]:
        """List all cycles for a project."""
        return await self._request(
            "GET", self._project_url(project_id, "cycles/")
        )

    async def create_cycle(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new cycle."""
        return await self._request(
            "POST", self._project_url(project_id, "cycles/"), json_data=data
        )

    async def get_cycle(self, project_id: str, cycle_id: str) -> dict[str, Any]:
        """Get a cycle by ID."""
        return await self._request(
            "GET", self._project_url(project_id, f"cycles/{cycle_id}/")
        )

    async def list_cycle_work_items(
        self, project_id: str, cycle_id: str
    ) -> dict[str, Any]:
        """List work items in a cycle."""
        return await self._request(
            "GET", self._project_url(project_id, f"cycles/{cycle_id}/cycle-issues/")
        )

    # ──────────────────────────────────────────────
    # Modules
    # ──────────────────────────────────────────────

    async def list_modules(self, project_id: str) -> dict[str, Any]:
        """List all modules for a project."""
        return await self._request(
            "GET", self._project_url(project_id, "modules/")
        )

    async def create_module(
        self, project_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new module."""
        return await self._request(
            "POST", self._project_url(project_id, "modules/"), json_data=data
        )

    async def get_module(self, project_id: str, module_id: str) -> dict[str, Any]:
        """Get a module by ID."""
        return await self._request(
            "GET", self._project_url(project_id, f"modules/{module_id}/")
        )

    async def list_module_work_items(
        self, project_id: str, module_id: str
    ) -> dict[str, Any]:
        """List work items in a module."""
        return await self._request(
            "GET",
            self._project_url(project_id, f"modules/{module_id}/module-issues/"),
        )

    # ──────────────────────────────────────────────
    # User & Members
    # ──────────────────────────────────────────────

    async def get_current_user(self) -> dict[str, Any]:
        """Get the currently authenticated user."""
        return await self._request("GET", "/api/v1/users/me/")

    async def list_workspace_members(self) -> dict[str, Any]:
        """List all members in the workspace."""
        return await self._request("GET", self._ws_url("members/"))

    async def list_project_members(self, project_id: str) -> dict[str, Any]:
        """List all members in a project."""
        return await self._request(
            "GET", self._project_url(project_id, "members/")
        )
