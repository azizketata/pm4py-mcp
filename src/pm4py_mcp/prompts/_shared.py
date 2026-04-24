"""Prompt helpers shared across all ``@mcp.prompt`` templates."""

from __future__ import annotations

from pm4py_mcp.tools.context import _get_context_for_prompts


def maybe_prepend_context(name: str = "default") -> str:
    """If a domain context is registered under ``name``, return a prose
    preamble that prompt bodies should prepend to their own instructions.
    Returns the empty string when no context is set, so callers can
    unconditionally concatenate.
    """
    ctx = _get_context_for_prompts(name)
    if not ctx:
        return ""
    return f"Domain context (registered via set_domain_context):\n\n{ctx}\n\n---\n\n"


def path_tip_footer(path_arg: str, kind: str = "event log") -> str:
    """Standardized footer telling Claude how to recover when a relative path
    fails to resolve inside the server's CWD.

    ``path_arg`` is the literal path string the user passed (interpolated into
    the error-remediation example). ``kind`` names the file type — ``"event log"``
    for XES/CSV/Parquet, ``"OCEL"`` for OCEL files. A generic phrasing is used
    for ``executive_summary``'s polymorphic ``log_id_or_path`` argument.
    """
    load_fn = "load_ocel" if kind == "OCEL" else "load_event_log"
    return (
        "\n\n---\n"
        f"**Path tip:** if `{path_arg}` is relative and `{load_fn}` returns "
        "`FileNotFoundError`, check the `server CWD:` line in the error message. "
        "Either retry with an absolute path (output of `realpath` or a full "
        "`C:\\...` path), or configure `PM4PY_MCP_CWD_HINT` in your MCP "
        "server's `env:` block to point at your project root. `~` is expanded "
        "server-side."
    )
