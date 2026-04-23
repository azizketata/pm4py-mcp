"""Prompt: ``/new_log_onboarding`` — 2-minute first-impression summary."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context
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
3. `abstract_log_features(log_id)` — textual description of log-level features.
4. `abstract_log_attributes(log_id)` — attribute distributions.
5. `abstract_variants(log_id)` — trace variants ranked by frequency.

Then write a ≤300-word first-impression summary covering:
- **Scale:** case count, event count, activity count, time window.
- **Process shape:** the dominant variant(s) and what they reveal.
- **Anomalies:** rare variants, unusual attribute distributions, gaps.
- **Next step:** one concrete follow-up (conformance check, bottleneck analysis, or filter-and-zoom).

Be concrete: cite activity names and counts drawn from the abstractions, not generalities."""
    return [UserMessage(preamble + body)]
