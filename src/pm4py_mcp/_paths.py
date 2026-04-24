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


def resolve_output_path(path: str, workspace: Path) -> Path:
    """Decide where to write a user-supplied output path.

    Rules (preserve 0.3.1 behavior, add hint fallback for the middle case):

    1. Absolute path → use as-is (user intent is explicit).
    2. Bare filename (no path separators) → land in ``workspace/``
       (unchanged from 0.3.1; documented as the "bare filename → workspace"
       convention across ``export_log``, ``export_ocel``, ``render_report``).
    3. Relative path with a directory component → try ``CWD / path``; if
       the parent directory doesn't exist yet, try ``HINT / path`` before
       falling back to CWD-resolution. This fixes the 0.3.1 "Known" issue
       where relative output paths with subdirs went to a surprising CWD.

    The hint is a *pure fallback* — it's consulted only when the relative
    path's parent directory doesn't already exist under CWD. Existing
    CWD-relative workflows keep working unchanged.
    """
    p = Path(path).expanduser()
    if p.is_absolute():
        return p
    if len(p.parts) == 1:
        return workspace / p
    # Relative with directory component.
    cwd_parent = (Path.cwd() / p).parent
    if cwd_parent.is_dir():
        return (Path.cwd() / p).resolve()
    hint = os.environ.get(ENV_HINT)
    if hint:
        hint_candidate = (Path(hint).expanduser() / p).resolve()
        if hint_candidate.parent.is_dir():
            return hint_candidate
    # Neither CWD-parent nor HINT-parent exists; fall back to CWD-relative
    # (caller will typically mkdir the parent themselves).
    return (Path.cwd() / p).resolve()


__all__ = ["ENV_HINT", "resolve_input_path", "resolve_output_path"]
