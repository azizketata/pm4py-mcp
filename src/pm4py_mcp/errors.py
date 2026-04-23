"""Custom exceptions for pm4py-mcp.

Tools raise these rather than returning error strings so FastMCP produces
proper `isError=true` responses the LLM can recover from. Each exception
carries a user-facing message; the MCP SDK wraps them in ToolError with
the class name preserved for structured handling.
"""

from __future__ import annotations


class Pm4pyMcpError(Exception):
    """Base class for all pm4py-mcp exceptions."""


class HandleNotFound(Pm4pyMcpError):
    """The given registry handle does not resolve (expired TTL or never existed)."""


class InvalidKind(Pm4pyMcpError):
    """A handle was passed to a tool expecting a different artifact kind."""


class UnsupportedFormat(Pm4pyMcpError):
    """File format cannot be inferred from extension or is not supported."""


class WorkspaceError(Pm4pyMcpError):
    """The workspace directory could not be created or written to."""


class GraphvizMissing(Pm4pyMcpError):
    """The `dot` system binary is required for visualizations but was not found on PATH.

    PM4Py's `save_vis_*` functions shell out to Graphviz; the Python bindings alone
    are not enough. Install from https://graphviz.org/download/ and restart the
    MCP server so the updated PATH is picked up.
    """


class OptionalDepMissing(Pm4pyMcpError):
    """An optional dependency required for the requested operation is not installed.

    Raised, e.g., when a user tries to load a relational (parquet-backed) OCEL
    without having installed the ``[ocel]`` extra (``pyarrow``). Carries the
    missing module name and the install hint so the LLM can surface an actionable
    remediation to the user.
    """

    def __init__(self, module: str, install_hint: str) -> None:
        self.module = module
        self.install_hint = install_hint
        super().__init__(
            f"Optional dependency {module!r} is not installed. "
            f"Install via `{install_hint}` and retry."
        )
