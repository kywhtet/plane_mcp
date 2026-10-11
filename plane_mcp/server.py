"""Plane MCP Server - registers all tools for the Plane API."""

from __future__ import annotations

import json
import os
import logging

from mcp.server.fastmcp import FastMCP
from plane_mcp.client import PlaneClient

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Server and Client Initialization
# ──────────────────────────────────────────────

# Read host and port from environment variables
_host = os.environ.get("MCP_HOST", "0.0.0.0")
_port = int(os.environ.get("MCP_PORT", "4200"))

mcp = FastMCP(
    "Plane MCP Server",
    instructions="MCP server for Plane project management. Manage projects, work items, cycles, modules, labels, states, and members.",
    host=_host,
    port=_port,
)


def _get_client() -> PlaneClient:
    """Create a PlaneClient from request headers/query params or fallback to environment variables."""
    # 1. Try to extract from current MCP request context (sent by remote clients like mcp-remote)
    headers: dict[str, str] = {}
    query_params: dict[str, str] = {}
    try:
        ctx = mcp.get_context()
        req = getattr(getattr(ctx, "request_context", None), "request", None)
        if req is not None:
            if hasattr(req, "headers"):
                headers = dict(req.headers)
            if hasattr(req, "query_params"):
                query_params = dict(req.query_params)
    except Exception:
        pass

    # Extract API key
    api_key = (
        headers.get("plane_api_key")
        or headers.get("x-plane-api-key")
        or headers.get("plane-api-key")
        or headers.get("authorization")
        or query_params.get("plane_api_key")
        or query_params.get("api_key")
        or os.environ.get("PLANE_API_KEY", "")
    )
    if api_key and api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()

    # Extract API URL
    api_url = (
        headers.get("plane_api_url")
        or headers.get("x-plane-api-url")
        or headers.get("plane-api-url")
        or query_params.get("plane_api_url")
        or query_params.get("api_url")
        or os.environ.get("PLANE_API_URL", "")
    )

    # Extract Workspace Slug
    workspace_slug = (
        headers.get("plane_workspace_slug")
        or headers.get("x-plane-workspace-slug")
        or headers.get("plane-workspace-slug")
        or query_params.get("plane_workspace_slug")
        or query_params.get("workspace_slug")
        or os.environ.get("PLANE_WORKSPACE_SLUG", "")
    )

    if not api_key:
        raise ValueError(
            "Plane API key is required. Pass it via client header 'PLANE_API_KEY' (or 'X-Plane-API-Key') or server environment variable PLANE_API_KEY."
        )
    if not api_url:
        raise ValueError(
            "Plane API URL is required. Pass it via client header 'PLANE_API_URL' (or 'X-Plane-API-Url') or server environment variable PLANE_API_URL."
        )
    if not workspace_slug:
        raise ValueError(
            "Plane workspace slug is required. Pass it via client header 'PLANE_WORKSPACE_SLUG' (or 'X-Plane-Workspace-Slug') or server environment variable PLANE_WORKSPACE_SLUG."
        )

    return PlaneClient(api_key=api_key, api_url=api_url, workspace_slug=workspace_slug)


def _format_response(data: dict | list) -> str:
    """Format API response as readable JSON."""
    return json.dumps(data, indent=2, default=str)


# ══════════════════════════════════════════════
# PROJECT TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def list_projects() -> str:
    """List all projects in the workspace.

    Returns a list of projects with their IDs, names, identifiers, and status.
    """
    client = _get_client()
    try:
        result = await client.list_projects()
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def get_project(project_id: str) -> str:
    """Get detailed information about a specific project.

    Args:
        project_id: The UUID of the project to retrieve.
    """
    client = _get_client()
    try:
        result = await client.get_project(project_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def create_project(
    name: str,
    identifier: str,
    description: str = "",
    project_lead: str | None = None,
    default_assignee: str | None = None,
) -> str:
    """Create a new project in the workspace.

    Args:
        name: The name of the project.
        identifier: Short unique identifier (e.g. "PROJ").
        description: Optional project description.
        project_lead: Optional UUID of the project lead user.
        default_assignee: Optional UUID of the default assignee.
    """
    data: dict = {"name": name, "identifier": identifier}
    if description:
        data["description"] = description
    if project_lead:
        data["project_lead"] = project_lead
    if default_assignee:
        data["default_assignee"] = default_assignee

    client = _get_client()
    try:
        result = await client.create_project(data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    project_lead: str | None = None,
    default_assignee: str | None = None,
) -> str:
    """Update an existing project.

    Args:
        project_id: The UUID of the project to update.
        name: New name for the project.
        description: New description.
        project_lead: New project lead UUID.
        default_assignee: New default assignee UUID.
    """
    data: dict = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if project_lead is not None:
        data["project_lead"] = project_lead
    if default_assignee is not None:
        data["default_assignee"] = default_assignee

    if not data:
        return json.dumps({"error": "No fields provided to update"})

    client = _get_client()
    try:
        result = await client.update_project(project_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def delete_project(project_id: str) -> str:
    """Delete a project. This action is irreversible.

    Args:
        project_id: The UUID of the project to delete.
    """
    client = _get_client()
    try:
        result = await client.delete_project(project_id)
        return _format_response(result)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# WORK ITEM TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def list_work_items(
    project_id: str,
    cursor: str | None = None,
    per_page: int | None = None,
    expand: str | None = None,
    fields: str | None = None,
    order_by: str | None = None,
) -> str:
    """List work items (issues) in a project with pagination support.

    Args:
        project_id: The UUID of the project.
        cursor: Pagination cursor (format: "page_size:offset:is_prev").
        per_page: Number of results per page (default 20, max 100).
        expand: Comma-separated related fields to expand (e.g. "state,assignees,created_by").
        fields: Comma-separated fields to include in response (e.g. "id,name,priority").
        order_by: Field to order by. Prefix with '-' for descending (e.g. "-created_at").
    """
    client = _get_client()
    try:
        result = await client.list_work_items(
            project_id,
            cursor=cursor,
            per_page=per_page,
            expand=expand,
            fields=fields,
            order_by=order_by,
        )
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def get_work_item(project_id: str, work_item_id: str) -> str:
    """Get detailed information about a specific work item.

    Args:
        project_id: The UUID of the project.
        work_item_id: The UUID of the work item.
    """
    client = _get_client()
    try:
        result = await client.get_work_item(project_id, work_item_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def create_work_item(
    project_id: str,
    name: str,
    description: str = "",
    priority: str = "none",
    state: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
    start_date: str | None = None,
    target_date: str | None = None,
    parent: str | None = None,
) -> str:
    """Create a new work item (issue) in a project.

    Args:
        project_id: The UUID of the project.
        name: Title/name of the work item.
        description: Description text.
        priority: Priority level: "urgent", "high", "medium", "low", or "none".
        state: UUID of the state to assign.
        assignees: List of user UUIDs to assign.
        labels: List of label UUIDs to attach.
        start_date: Start date in YYYY-MM-DD format.
        target_date: Target/due date in YYYY-MM-DD format.
        parent: UUID of parent work item (for sub-issues).
    """
    data: dict = {"name": name}
    if description:
        data["description_html"] = f"<p>{description}</p>"
    if priority != "none":
        data["priority"] = priority
    if state:
        data["state"] = state
    if assignees:
        data["assignees"] = assignees
    if labels:
        data["labels"] = labels
    if start_date:
        data["start_date"] = start_date
    if target_date:
        data["target_date"] = target_date
    if parent:
        data["parent"] = parent

    client = _get_client()
    try:
        result = await client.create_work_item(project_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def update_work_item(
    project_id: str,
    work_item_id: str,
    name: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
    start_date: str | None = None,
    target_date: str | None = None,
) -> str:
    """Update an existing work item.

    Args:
        project_id: The UUID of the project.
        work_item_id: The UUID of the work item to update.
        name: New title/name.
        description: New description text.
        priority: New priority: "urgent", "high", "medium", "low", or "none".
        state: New state UUID.
        assignees: New list of assignee UUIDs (replaces existing).
        labels: New list of label UUIDs (replaces existing).
        start_date: New start date (YYYY-MM-DD).
        target_date: New target date (YYYY-MM-DD).
    """
    data: dict = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description_html"] = f"<p>{description}</p>"
    if priority is not None:
        data["priority"] = priority
    if state is not None:
        data["state"] = state
    if assignees is not None:
        data["assignees"] = assignees
    if labels is not None:
        data["labels"] = labels
    if start_date is not None:
        data["start_date"] = start_date
    if target_date is not None:
        data["target_date"] = target_date

    if not data:
        return json.dumps({"error": "No fields provided to update"})

    client = _get_client()
    try:
        result = await client.update_work_item(project_id, work_item_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def delete_work_item(project_id: str, work_item_id: str) -> str:
    """Delete a work item. This action is irreversible.

    Args:
        project_id: The UUID of the project.
        work_item_id: The UUID of the work item to delete.
    """
    client = _get_client()
    try:
        result = await client.delete_work_item(project_id, work_item_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def search_work_items(
    search: str,
    project_id: str | None = None,
    limit: int | None = None,
    workspace_search: bool = True,
) -> str:
    """Search work items by name, description, or identifier.

    Args:
        search: Search query string.
        project_id: Optional project UUID to restrict search scope.
        limit: Maximum number of results to return.
        workspace_search: If True, search across the entire workspace. If False, search within a specific project.
    """
    client = _get_client()
    try:
        result = await client.search_work_items(
            search=search,
            project_id=project_id,
            limit=limit,
            workspace_search=workspace_search,
        )
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def add_comment(
    project_id: str,
    work_item_id: str,
    comment_html: str,
) -> str:
    """Add a comment to a work item.

    Args:
        project_id: The UUID of the project.
        work_item_id: The UUID of the work item.
        comment_html: The comment body in HTML format (e.g. "<p>My comment</p>").
    """
    data = {"comment_html": comment_html}
    client = _get_client()
    try:
        result = await client.add_comment(project_id, work_item_id, data)
        return _format_response(result)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# STATE TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def list_states(project_id: str) -> str:
    """List all workflow states for a project.

    States define the workflow stages (e.g., Backlog, Todo, In Progress, Done).

    Args:
        project_id: The UUID of the project.
    """
    client = _get_client()
    try:
        result = await client.list_states(project_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def create_state(
    project_id: str,
    name: str,
    group: str,
    color: str = "#000000",
    description: str = "",
) -> str:
    """Create a new workflow state for a project.

    Args:
        project_id: The UUID of the project.
        name: Display name of the state (e.g. "In Review").
        group: State group. Must be one of: "backlog", "unstarted", "started", "completed", "cancelled".
        color: Hex color code for the state (e.g. "#ff9900").
        description: Optional description of the state.
    """
    data: dict = {"name": name, "group": group, "color": color}
    if description:
        data["description"] = description

    client = _get_client()
    try:
        result = await client.create_state(project_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def get_state(project_id: str, state_id: str) -> str:
    """Get details of a specific workflow state.

    Args:
        project_id: The UUID of the project.
        state_id: The UUID of the state.
    """
    client = _get_client()
    try:
        result = await client.get_state(project_id, state_id)
        return _format_response(result)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# LABEL TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def list_labels(project_id: str) -> str:
    """List all labels for a project.

    Labels are used to tag and categorize work items.

    Args:
        project_id: The UUID of the project.
    """
    client = _get_client()
    try:
        result = await client.list_labels(project_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def create_label(
    project_id: str,
    name: str,
    color: str = "#000000",
    description: str = "",
) -> str:
    """Create a new label for a project.

    Args:
        project_id: The UUID of the project.
        name: Display name of the label (e.g. "bug", "feature").
        color: Hex color code for the label (e.g. "#ff0000").
        description: Optional description of the label.
    """
    data: dict = {"name": name, "color": color}
    if description:
        data["description"] = description

    client = _get_client()
    try:
        result = await client.create_label(project_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def get_label(project_id: str, label_id: str) -> str:
    """Get details of a specific label.

    Args:
        project_id: The UUID of the project.
        label_id: The UUID of the label.
    """
    client = _get_client()
    try:
        result = await client.get_label(project_id, label_id)
        return _format_response(result)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# CYCLE TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def list_cycles(project_id: str) -> str:
    """List all cycles for a project.

    Cycles are time-boxed iterations for organizing work items.

    Args:
        project_id: The UUID of the project.
    """
    client = _get_client()
    try:
        result = await client.list_cycles(project_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def create_cycle(
    project_id: str,
    name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    description: str = "",
) -> str:
    """Create a new cycle for a project.

    Args:
        project_id: The UUID of the project.
        name: Name of the cycle (e.g. "Sprint 1").
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        description: Optional description.
    """
    data: dict = {"name": name}
    if start_date:
        data["start_date"] = start_date
    if end_date:
        data["end_date"] = end_date
    if description:
        data["description"] = description

    client = _get_client()
    try:
        result = await client.create_cycle(project_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def get_cycle(project_id: str, cycle_id: str) -> str:
    """Get details of a specific cycle.

    Args:
        project_id: The UUID of the project.
        cycle_id: The UUID of the cycle.
    """
    client = _get_client()
    try:
        result = await client.get_cycle(project_id, cycle_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def list_cycle_work_items(project_id: str, cycle_id: str) -> str:
    """List all work items assigned to a specific cycle.

    Args:
        project_id: The UUID of the project.
        cycle_id: The UUID of the cycle.
    """
    client = _get_client()
    try:
        result = await client.list_cycle_work_items(project_id, cycle_id)
        return _format_response(result)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# MODULE TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def list_modules(project_id: str) -> str:
    """List all modules for a project.

    Modules are used to group related work items by feature or component.

    Args:
        project_id: The UUID of the project.
    """
    client = _get_client()
    try:
        result = await client.list_modules(project_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def create_module(
    project_id: str,
    name: str,
    start_date: str | None = None,
    target_date: str | None = None,
    description: str = "",
    status: str = "backlog",
) -> str:
    """Create a new module for a project.

    Args:
        project_id: The UUID of the project.
        name: Name of the module (e.g. "Authentication").
        start_date: Start date in YYYY-MM-DD format.
        target_date: Target date in YYYY-MM-DD format.
        description: Optional description.
        status: Module status: "backlog", "planned", "in-progress", "paused", "completed", "cancelled".
    """
    data: dict = {"name": name, "status": status}
    if start_date:
        data["start_date"] = start_date
    if target_date:
        data["target_date"] = target_date
    if description:
        data["description"] = description

    client = _get_client()
    try:
        result = await client.create_module(project_id, data)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def get_module(project_id: str, module_id: str) -> str:
    """Get details of a specific module.

    Args:
        project_id: The UUID of the project.
        module_id: The UUID of the module.
    """
    client = _get_client()
    try:
        result = await client.get_module(project_id, module_id)
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def list_module_work_items(project_id: str, module_id: str) -> str:
    """List all work items assigned to a specific module.

    Args:
        project_id: The UUID of the project.
        module_id: The UUID of the module.
    """
    client = _get_client()
    try:
        result = await client.list_module_work_items(project_id, module_id)
        return _format_response(result)
    finally:
        await client.close()


# ══════════════════════════════════════════════
# USER & MEMBER TOOLS
# ══════════════════════════════════════════════


@mcp.tool()
async def get_current_user() -> str:
    """Get the currently authenticated user's profile information."""
    client = _get_client()
    try:
        result = await client.get_current_user()
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def list_workspace_members() -> str:
    """List all members in the workspace with their roles."""
    client = _get_client()
    try:
        result = await client.list_workspace_members()
        return _format_response(result)
    finally:
        await client.close()


@mcp.tool()
async def list_project_members(project_id: str) -> str:
    """List all members assigned to a specific project.

    Args:
        project_id: The UUID of the project.
    """
    client = _get_client()
    try:
        result = await client.list_project_members(project_id)
        return _format_response(result)
    finally:
        await client.close()


# ──────────────────────────────────────────────
# SSE / HTTP transport helpers
# ──────────────────────────────────────────────

def run_sse(host: str = "0.0.0.0", port: int = 4200):
    """Run the MCP server over SSE transport."""
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="sse")


def run_http(host: str = "0.0.0.0", port: int = 4200):
    """Run the MCP server over streamable HTTP transport."""
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
