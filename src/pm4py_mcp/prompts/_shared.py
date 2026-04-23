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
