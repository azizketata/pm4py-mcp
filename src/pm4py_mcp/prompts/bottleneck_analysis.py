"""Prompt: ``/bottleneck_analysis`` — find slowest variants and bottleneck edges."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="bottleneck_analysis",
    title="Bottleneck analysis",
    description="Identify slow variants and bottleneck activity edges from the log's performance profile.",
)
def bottleneck_analysis(log_path: str) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Find bottlenecks in the log at `{log_path}`.

Steps:
1. `load_event_log(path="{log_path}")` → log_id.
2. `describe_log(log_id)` — overall shape.
3. `abstract_log_features(log_id)` — concurrency and timing signal at log level.
4. `get_case_durations(log_id)` — p50, p75, p90, p95, p99 percentiles. How skewed is the duration distribution?
5. `abstract_variants(log_id, include_performance=True)` — per-variant durations.
6. `abstract_dfg(log_id, include_performance=True)` — sojourn times per activity transition.
7. `discover_dfg(log_id)` → `visualize_dfg` — render the DFG so you can point at the slow edges.

Then report:
- **Top 3 slowest variants** by median/p90 duration. What distinguishes them?
- **Top 3 bottleneck edges** (activity-pair transitions with the longest sojourn times).
- **Hypothesis**: which specific handoff or activity most likely causes the slowdown?
- **Next step**: propose a filter (e.g. `filter_case_performance`) that would isolate the slow cohort for deeper analysis with `abstract_case`."""
    return [UserMessage(preamble + body)]
