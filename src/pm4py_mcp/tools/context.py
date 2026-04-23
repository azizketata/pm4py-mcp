"""Domain context store for prompt templates.

Users with a specific process (SAP order-to-cash, a hospital triage protocol,
a loan-application SOP) can register a textual domain description that every
prompt template in ``pm4py_mcp.prompts`` prepends to its instructions. This
is the pm4py-mcp equivalent of Celonis's "Knowledge Model" — a lightweight
session-wide blob of domain knowledge Claude reasons over alongside the log.

Kept in a separate module-level dict, **not** in the shared ``LogRegistry`` —
the LRU's 8-slot cap is wrong for small, sticky context strings. Capped at
16 named contexts and 20 KB per entry so a runaway SOP paste can't blow the
response budget.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pm4py_mcp._tokens import estimate_tokens
from pm4py_mcp.errors import Pm4pyMcpError, UnsupportedFormat, WorkspaceError
from pm4py_mcp.server import mcp

_MAX_CONTEXT_BYTES = 20_000
_WARN_CONTEXT_BYTES = 10_000
_MAX_CONTEXTS = 16

# Module-level store; survives across tool calls in the same server process.
_contexts: dict[str, str] = {}


class ContextNotFound(Pm4pyMcpError):
    """Raised by ``get_domain_context`` when the requested name is not registered."""


def _resolve_text_or_path(text_or_path: str) -> tuple[str, str]:
    """Return (content, source_label). Treat the argument as a file path only
    if it resolves to an existing readable file; otherwise treat as inline text."""
    try:
        p = Path(text_or_path).expanduser()
    except (OSError, ValueError):
        return text_or_path, "inline text"
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8"), f"file: {p}"
        except OSError as exc:
            raise WorkspaceError(f"Could not read context file {p}: {exc}") from exc
    return text_or_path, "inline text"


@mcp.tool()
def set_domain_context(
    text_or_path: str,
    name: str = "default",
) -> dict[str, Any]:
    """Register a domain context (SOP, glossary, process description) under ``name``.

    ``text_or_path`` is treated as a **file path** if it resolves to an existing
    readable file; otherwise as **inline text**. Subsequent calls with the same
    ``name`` overwrite the stored value. Subsequent prompt invocations prepend
    the stored context to their instructions.

    Limits: 20 KB per context (raises ``WorkspaceError`` if exceeded),
    16 named contexts max.
    """
    content, source = _resolve_text_or_path(text_or_path)
    size_bytes = len(content.encode("utf-8"))

    if size_bytes > _MAX_CONTEXT_BYTES:
        raise WorkspaceError(
            f"Context {name!r} is {size_bytes} bytes, exceeds {_MAX_CONTEXT_BYTES}-byte limit. "
            "Trim it or split into multiple named contexts."
        )

    if name not in _contexts and len(_contexts) >= _MAX_CONTEXTS:
        raise WorkspaceError(
            f"Too many stored domain contexts ({len(_contexts)}/{_MAX_CONTEXTS}). "
            "Remove existing contexts before registering a new one."
        )

    _contexts[name] = content
    return {
        "name": name,
        "source": source,
        "size_bytes": size_bytes,
        "approx_tokens": estimate_tokens(content),
        "warning_large": size_bytes > _WARN_CONTEXT_BYTES,
        "stored_context_count": len(_contexts),
    }


@mcp.tool()
def get_domain_context(name: str = "default") -> dict[str, Any]:
    """Retrieve a previously-stored domain context.

    Raises :class:`ContextNotFound` if the name is not registered.
    """
    if name not in _contexts:
        raise ContextNotFound(
            f"No domain context named {name!r}. "
            f"Known contexts: {sorted(_contexts.keys()) or '[]'}. "
            "Call set_domain_context to register one."
        )
    content = _contexts[name]
    return {
        "name": name,
        "content": content,
        "size_bytes": len(content.encode("utf-8")),
        "approx_tokens": estimate_tokens(content),
    }


def _get_context_for_prompts(name: str = "default") -> str | None:
    """Internal helper — used by prompt templates to prepend context.

    Returns ``None`` when no context is set. Not exposed as an MCP tool.
    """
    return _contexts.get(name)


def _clear_all_for_tests() -> None:
    """Testing hook — clears the in-memory context store. Never called in prod."""
    _contexts.clear()


# Re-export UnsupportedFormat so the import lives next to the tools that use it
_ = UnsupportedFormat

__all__ = [
    "ContextNotFound",
    "get_domain_context",
    "set_domain_context",
]
