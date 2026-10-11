# Plane MCP Server

MCP server for interacting with Plane project management via the Model Context Protocol.

## Setup

```bash
# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env with your API key and workspace slug
```

## Running

```bash
# stdio transport (default, for Claude Desktop)
python -m plane_mcp

# SSE transport (for remote connections)
python -m plane_mcp --transport sse --port 8000

# HTTP transport (streamable HTTP)
python -m plane_mcp --transport http --port 8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PLANE_API_KEY` | Yes | Your Plane API key |
| `PLANE_API_URL` | Yes | Base URL of your Plane instance |
| `PLANE_WORKSPACE_SLUG` | Yes | Your workspace slug |
| `MCP_TRANSPORT` | No | Transport mode: stdio, sse, http (default: stdio) |
| `MCP_HOST` | No | Host for SSE/HTTP (default: 0.0.0.0) |
| `MCP_PORT` | No | Port for SSE/HTTP (default: 8000) |

## Available Tools

### Projects
- `list_projects` - List all projects in the workspace
- `get_project` - Get project details by ID
- `create_project` - Create a new project
- `update_project` - Update an existing project
- `delete_project` - Delete a project

### Work Items
- `list_work_items` - List work items in a project (with pagination, expand, fields)
- `get_work_item` - Get a specific work item
- `create_work_item` - Create a new work item
- `update_work_item` - Update a work item
- `delete_work_item` - Delete a work item
- `search_work_items` - Search across work items in workspace
- `add_comment` - Add a comment to a work item

### States
- `list_states` - List workflow states for a project
- `create_state` - Create a new state
- `get_state` - Get state details

### Labels
- `list_labels` - List labels for a project
- `create_label` - Create a new label
- `get_label` - Get label details

### Cycles
- `list_cycles` - List cycles in a project
- `create_cycle` - Create a new cycle
- `get_cycle` - Get cycle details
- `list_cycle_work_items` - List work items in a cycle

### Modules
- `list_modules` - List modules in a project
- `create_module` - Create a new module
- `get_module` - Get module details
- `list_module_work_items` - List work items in a module

### User & Members
- `get_current_user` - Get the authenticated user
- `list_workspace_members` - List workspace members
- `list_project_members` - List project members

## MCP Client JSON Configuration

You can configure any MCP-compatible client (Claude Desktop, Cursor, Windsurf, etc.) by passing Plane credentials directly in the JSON config's `env` block. **No `.env` file needed** — the env keys in the JSON config take priority.

### Option 1: Direct Python (stdio transport)

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "plane": {
      "command": "python",
      "args": ["-m", "plane_mcp"],
      "env": {
        "PLANE_API_KEY": "plane_api_1970250fb579422e8c3244dea78f77e0",
        "PLANE_API_URL": "https://pm.agbisp.net",
        "PLANE_WORKSPACE_SLUG": "intelligent-and-network-operations"
      }
    }
  }
}
```

### Option 2: Via `mcp-remote` (SSE transport)

First start the server:

```bash
python3 -m plane_mcp --transport sse --port 8000
```

Then configure your MCP client to connect via `mcp-remote`:

```json
{
  "mcpServers": {
    "mcp-remote-plane": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://127.0.0.1:8000/sse",
        "--allow-http"
      ],
      "env": {
        "PLANE_API_KEY": "plane_api_1970250fb579422e8c3244dea78f77e0",
        "PLANE_API_URL": "https://pm.agbisp.net",
        "PLANE_WORKSPACE_SLUG": "intelligent-and-network-operations"
      }
    }
  }
}
```

### Option 3: Via Docker Container (SSE transport)

First start the Docker container:

```bash
docker compose up --build -d
```

Then configure your MCP client to connect via `mcp-remote` (note the port is `3700` for Docker):

```json
{
  "mcpServers": {
    "mcp-remote-plane": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://127.0.0.1:3700/sse",
        "--allow-http"
      ],
      "env": {
        "PLANE_API_KEY": "plane_api_1970250fb579422e8c3244dea78f77e0",
        "PLANE_API_URL": "https://pm.agbisp.net",
        "PLANE_WORKSPACE_SLUG": "intelligent-and-network-operations"
      }
    }
  }
}
```

> **Note:** Environment variables set via the JSON `env` block take priority over values in a `.env` file.
# plane_mcp
