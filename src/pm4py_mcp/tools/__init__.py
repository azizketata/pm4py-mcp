"""Phase 1 tool registration.

Importing this package has a side effect: each submodule imports the
``mcp`` + ``registry`` singletons from ``pm4py_mcp.server`` and decorates
its handlers with ``@mcp.tool()``. That means the tools are registered
purely by side-effect; no explicit ``register_tools()`` call is needed.

Ordering does not matter — each submodule is independent.
"""

from __future__ import annotations

from pm4py_mcp.tools import (  # noqa: F401
    conformance,
    discovery,
    filters,
    io,
    ocel_discovery,
    ocel_filters,
    ocel_io,
    ocel_visualization,
    stats,
    visualization,
)

__all__: list[str] = []
