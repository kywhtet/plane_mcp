"""Entry point for the Plane MCP server."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv


class _IgnorePreInitWarnings(logging.Filter):
    """Drop the harmless race-condition warning emitted when an MCP client
    sends a request before the initialization handshake is complete.
    The server already handles this gracefully (returns INVALID_PARAMS).
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        return "before initialization was complete" not in record.getMessage()


def _patch_server_session() -> None:
    """Monkey-patch ServerSession to tolerate missing 'initialized' notifications.

    Some MCP clients (mcp-remote, certain Claude Desktop versions) skip sending
    the 'initialized' notification after the initialize handshake completes.
    This leaves the session permanently in the 'Initializing' state, causing
    every subsequent tool call to be rejected with -32602 INVALID_PARAMS.

    The patch intercepts tool requests arriving while state == Initializing and
    auto-advances the state to Initialized, matching what the missing notification
    would have done.
    """
    try:
        import mcp.types as _types
        from mcp.server.session import InitializationState, ServerSession
    except (ImportError, AttributeError):
        logging.getLogger(__name__).debug(
            "Skipping ServerSession patch: InitializationState not present in this MCP SDK version."
        )
        return

    _orig = ServerSession._received_request

    async def _patched(self, responder):  # type: ignore[no-untyped-def]
        if self._initialization_state == InitializationState.Initializing:
            match responder.request.root:
                case _types.InitializeRequest() | _types.PingRequest():
                    pass  # Let the original handler manage these.
                case _:
                    # Tool / resource / other request arrived before 'initialized'
                    # notification — auto-complete initialization so the request
                    # isn't rejected.
                    logging.getLogger(__name__).debug(
                        "Auto-completing MCP initialization (client skipped "
                        "'initialized' notification)."
                    )
                    self._initialization_state = InitializationState.Initialized
        await _orig(self, responder)

    ServerSession._received_request = _patched  # type: ignore[method-assign]


def main():
    """Parse arguments and run the MCP server with the selected transport."""
    # Suppress the harmless "before initialization was complete" warning.
    logging.getLogger("mcp.shared.session").addFilter(_IgnorePreInitWarnings())
    # Patch ServerSession to handle clients that skip the 'initialized' notification.
    _patch_server_session()

    # Load .env file; override=False ensures env vars passed via MCP JSON
    # config ("env" block) or shell take priority over .env file values.
    load_dotenv(override=False)

    parser = argparse.ArgumentParser(description="Plane MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host for SSE/HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "4200")),
        help="Port for SSE/HTTP transport (default: 4200)",
    )
    args = parser.parse_args()

    # Validate required env vars early if running in local stdio mode.
    # In remote network modes (SSE / HTTP), clients (e.g. via mcp-remote) can provide
    # PLANE_API_KEY, PLANE_WORKSPACE_SLUG, PLANE_API_URL dynamically per connection/request.
    required_vars = ["PLANE_API_KEY", "PLANE_API_URL", "PLANE_WORKSPACE_SLUG"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing and args.transport == "stdio":
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Set them via the MCP JSON config 'env' block, a .env file, or as shell environment variables.")
        sys.exit(1)
    elif missing:
        print(f"Notice: Server running without hardcoded credentials ({', '.join(missing)}).")
        print("Connecting clients should provide their credentials via HTTP headers (e.g., mcp-remote --header) or query parameters.")

    # Import server
    from plane_mcp.server import mcp

    # Apply parsed host and port to server settings
    if args.host:
        mcp.settings.host = args.host
    if args.port:
        mcp.settings.port = args.port

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse")
    elif args.transport == "http":
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
