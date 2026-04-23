"""FastMCP server exposing the Phase 0 walking-skeleton tool surface.

Phase 0 ships exactly one tool (`ping`) whose only job is to prove the
end-to-end transport: client -> stdio -> FastMCP -> tool -> response.
No PM4Py imports land in tool bodies until Phase 1.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from pm4py_mcp import __version__

mcp: FastMCP = FastMCP("pm4py-mcp")


@mcp.tool()
def ping() -> str:
    """Health-check tool. Returns the server name and version.

    Used by the testing pyramid and by humans verifying that a freshly
    installed server is reachable from their MCP client (Claude Desktop,
    Claude Code, MCP Inspector).
    """
    return f"pong pm4py-mcp {__version__}"


def main() -> None:
    """Entry point registered as the `pm4py-mcp` console script.

    Runs the server on stdio. Streamable HTTP is a Phase 4 addition and
    is intentionally not wired up here.
    """
    mcp.run()


if __name__ == "__main__":
    main()
