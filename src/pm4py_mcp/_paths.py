"""User-path resolution with a ``PM4PY_MCP_CWD_HINT`` env-var fallback.

When Claude Code / Claude Desktop launches the server via ``uvx``, the
subprocess inherits a CWD that is frequently *not* the user's project
root. A prompt with a relative path (``examples/benchmarks/sepsis.xes.gz``)
then resolves against the wrong CWD and the user hits ``FileNotFoundError``
with no clue what went wrong.

The fallback: if the initial ``Path(path).expanduser().resolve()`` doesn't
exist and the input was relative, try anchoring against
``os.environ["PM4PY_MCP_CWD_HINT"]`` before giving up. Users configure the
hint once in their MCP server block::

    "pm4py": {
      "command": "uvx",
      "args": ["pm4py-mcp@latest"],
      "env": { "PM4PY_MCP_CWD_HINT": "${workspaceFolder}" }
    }

The hint is a *pure fallback* — an absolute path or a relative path that
resolves correctly against CWD is never overridden.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_HINT = "PM4PY_MCP_CWD_HINT"


def resolve_input_path(path: str, kind: str) -> Path:
    """Resolve a user-supplied ``path`` to an existing file.

    Order of attempts:
    1. If ``path`` is absolute, check it exists and return (no hint lookup).
    2. If ``path`` is relative, try ``Path(path).expanduser().resolve()``
       against the current CWD.
    3. If that fails and ``PM4PY_MCP_CWD_HINT`` is set, try
       ``Path(hint) / path`` and resolve that.

    On every failure path, raise ``FileNotFoundError`` whose message names
    the input, the server CWD, and whether the hint was set — so Claude (or
    a human) can act on the error instead of guessing.

    ``kind`` is a short noun used in the error message (``"event log"``,
    ``"OCEL file"``, etc.) — callers should use a phrase the user would
    recognize in context.
    """
    p = Path(path).expanduser()
    if p.is_absolute():
        if p.is_file():
            return p
    else:
        resolved = p.resolve()
        if resolved.is_file():
            return resolved
        hint = os.environ.get(ENV_HINT)
        if hint:
            alt = (Path(hint).expanduser() / p).resolve()
            if alt.is_file():
                return alt

    hint_value = os.environ.get(ENV_HINT, "(not set)")
    raise FileNotFoundError(
        f"{kind} not found.\n"
        f"  input path: {path!r}\n"
        f"  server CWD: {os.getcwd()}\n"
        f"  {ENV_HINT}: {hint_value}\n"
        f"  Retry with an absolute path, or set {ENV_HINT} in your MCP "
        f"server config to the directory the relative path is anchored to."
    )


__all__ = ["ENV_HINT", "resolve_input_path"]
