"""FastMCP server.

Holds the two module-level singletons the tool modules attach to:

* ``mcp``      — the ``FastMCP`` instance that owns tool registrations.
* ``registry`` — the in-process :class:`LogRegistry` holding logs + models.

Tool modules import those singletons and decorate handlers with
``@mcp.tool()``. The import near the bottom of this file is what triggers
the decorator evaluation; removing it silently drops all Phase 1 tools.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from pm4py_mcp import __version__
from pm4py_mcp.registry import LogRegistry

mcp: FastMCP = FastMCP("pm4py-mcp")
registry: LogRegistry = LogRegistry()


@mcp.tool()
def ping() -> str:
    """Health-check tool. Returns the server name and version.

    Used by the testing pyramid and by humans verifying that a freshly
    installed server is reachable from their MCP client (Claude Desktop,
    Claude Code, MCP Inspector).
    """
    return f"pong pm4py-mcp {__version__}"


def main() -> None:
    """Entry point registered as the ``pm4py-mcp`` console script.

    Runs the server on stdio. Streamable HTTP is a Phase 4 addition and
    is intentionally not wired up here.
    """
    mcp.run()


# Phase 1+2 tool + Phase 3 prompt registration. Imported for side effects
# (decorator evaluation). Must come after ``mcp`` and ``registry`` are defined
# above — tool and prompt modules import those singletons at module load.
from pm4py_mcp import prompts as _prompts  # noqa: E402, F401
from pm4py_mcp import tools as _tools  # noqa: E402, F401

if __name__ == "__main__":
    main()
