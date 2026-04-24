"""Prompt: ``/new_log_onboarding`` — 2-minute first-impression summary."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context, path_tip_footer
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="new_log_onboarding",
    title="New log onboarding",
    description="Produce a ≤300-word first-impression summary of an unfamiliar event log.",
)
def new_log_onboarding(log_path: str) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Walk me through the unfamiliar log at `{log_path}`. Execute these tools in order:

1. `load_event_log(path="{log_path}")` — get a log_id.
2. `describe_log(log_id)` — case/event counts, activities preview, time range.
3. `get_case_durations(log_id)` — p50/p75/p90/p95/p99 percentiles. If p90/p50 > 5, flag the long tail as the headline anomaly.
4. `get_variants(log_id, top_k=10)` — top-10 variants with counts. Cheap and structured; gives you the dominant-path coverage percentage.
5. `abstract_log_features(log_id)` — textual log-level feature signal (activity frequencies, succession counts).
6. `abstract_log_attributes(log_id)` — attribute distributions (numeric quantiles, categorical value frequencies).
7. (Optional — only if step 4 surfaces a long variant worth explaining) `abstract_variants(log_id, max_len=3000)` for per-variant performance prose.

Then write a ≤300-word first-impression summary covering:
- **Scale:** case count, event count, activity count, time window.
- **Duration profile:** median and p90; call out the tail when p90/p50 > 5. Note that `get_case_durations` measures case *lifetime* (first to last event), not hospital/bed time — for logs where one case can span multiple visits (readmission-style), a long tail may reflect outpatient gaps rather than throughput bottlenecks. When the tail is dramatic, check whether cases end on `Return *`, `Readmit`, or a similar revisit activity before calling the process "slow".
- **Process shape:** dominant variants from step 4 and what they reveal.
- **Anomalies:** rare variants, unusual attribute distributions, protocol deviations.
- **Next step:** one concrete follow-up (conformance check, bottleneck analysis, or filter-and-zoom). If you want to inspect a specific case, call `sample_case_ids(log_id, n=3, strategy="longest")` then `abstract_case(log_id, case_id=<one of those>)`.

Be concrete: cite activity names, case counts, and duration numbers drawn from the tool outputs — not generalities."""
    return [UserMessage(preamble + body + path_tip_footer(log_path))]
