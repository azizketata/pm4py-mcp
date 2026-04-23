"""Workspace directory management.

Derived artifacts (PNG/SVG renders, exported logs, conformance CSVs) live
under `~/.pm4py-mcp/workspace/` by default, overrideable via the
`PM4PY_MCP_WORKSPACE` environment variable (absolute or `~`-relative path).

State does not persist across client restarts — the registry is in-memory,
but workspace files DO persist on disk so users can open the rendered
PNG/SVG after their Claude session ends.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from pm4py_mcp.errors import WorkspaceError

ENV_VAR = "PM4PY_MCP_WORKSPACE"
DEFAULT_SUBDIR = Path(".pm4py-mcp") / "workspace"


def workspace_dir() -> Path:
    """Return the absolute workspace directory path without creating it."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / DEFAULT_SUBDIR).resolve()


def ensure_workspace() -> Path:
    """Return the workspace directory, creating it (and parents) if missing."""
    d = workspace_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(f"Could not create workspace at {d}: {exc}") from exc
    return d


def derived_path(stem: str, ext: str, *, unique: bool = True) -> Path:
    """Return an absolute path in the workspace for a derived artifact.

    Parameters
    ----------
    stem
        Base filename without extension. Must not contain path separators.
    ext
        File extension with or without leading dot (e.g. ``"png"`` or ``".png"``).
    unique
        If True (default), append a short random suffix to avoid collisions
        across concurrent tool calls sharing the same stem.
    """
    if "/" in stem or "\\" in stem or os.sep in stem:
        raise WorkspaceError(f"stem must not contain path separators: {stem!r}")
    if not ext.startswith("."):
        ext = "." + ext
    base = ensure_workspace()
    if unique:
        suffix = uuid.uuid4().hex[:6]
        return base / f"{stem}-{suffix}{ext}"
    return base / f"{stem}{ext}"
