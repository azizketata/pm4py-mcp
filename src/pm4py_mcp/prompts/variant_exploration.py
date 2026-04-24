"""Prompt: ``/variant_exploration`` — top-k variants, drill into the dominant one."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context, path_tip_footer
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="variant_exploration",
    title="Variant exploration",
    description="Survey the top-k trace variants and build a Petri net of the dominant one.",
)
def variant_exploration(log_path: str, k: int = 5) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Survey the top-{k} variants of the log at `{log_path}`.

Steps:
1. `load_event_log(path="{log_path}")` → log_id.
2. `get_variants(log_id, top_k={k})` — list the {k} most common variants with counts.
3. `abstract_variants(log_id)` — richer per-variant description in text.
4. `filter_variants(log_id, top_k=1, retain=True)` → log_id_top (the log restricted to the single dominant variant).
5. `describe_log(log_id_top)` — confirm the filter reduced correctly.
6. `discover_petri_net(log_id_top, algorithm="inductive")` → pn_top.
7. `visualize_petri_net(pn_top)` — render the dominant variant's process shape.

Then report:
- The {k} most common variants, each with count and percentage of total.
- Total case coverage of the top {k}.
- Whether the top variant looks like a **happy path** or shows signs of rework (loops, skipped steps).
- Attach the Petri net of the dominant variant."""
    return [UserMessage(preamble + body + path_tip_footer(log_path))]
