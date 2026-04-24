"""Prompt: ``/organizational_analysis`` — team structure + handoff patterns from resources."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context, path_tip_footer
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="organizational_analysis",
    title="Organizational analysis",
    description="Map team structure, handoff patterns, and resource roles from a log's resource attribute.",
)
def organizational_analysis(log_path: str) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Investigate the organizational structure of the log at `{log_path}`.

**Prerequisite:** this workflow requires an ``org:resource`` attribute in the log. If `describe_log` shows no `org:resource` column, STOP and report that this log doesn't support organizational mining — don't try to chain the discover_* tools.

Steps:
1. `load_event_log(path="{log_path}")` → log_id.
2. `describe_log(log_id)` — confirm the log has case/event counts + check for `org:resource` attribute (the activity preview may hint at whether resources are recorded).
3. `discover_handover_network(log_id)` → handover_sna_id. An edge A → B means resource A's work was directly followed by resource B's within a case.
4. `abstract_sna(handover_sna_id, top_k=10)` — read the strongest handoff patterns in prose.
5. `discover_working_together_network(log_id)` → collab_sna_id. An edge A ↔ B means A and B participated in the same case.
6. `abstract_sna(collab_sna_id, top_k=10)` — see who collaborates most often.
7. `discover_organizational_roles(log_id)` → roles_id. Clusters of resources by activity-profile similarity.

Then write a ≤300-word organizational summary covering:
- **Team size & shape:** total resources, number of distinct roles.
- **Dominant handoffs:** top 2-3 handover edges — who passes work to whom most often?
- **Network sources & sinks:** resources who receive but never hand off (endpoints), resources who initiate but never receive (entry points).
- **Role clusters:** the most populous role(s) and the activities that define them. If multiple resources share a role, they're interchangeable for that activity set.
- **Bottleneck resources:** any resource that dominates a specific handoff edge (>50% of handoffs) — they're a capacity constraint.
- **Next step:** one concrete follow-up (e.g., `filter_attribute_values(log_id, attribute='org:resource', values=[<resource>], level='event')` to examine one resource's workload, or `visualize_dotted_chart(log_id, attributes=['org:resource', 'time:timestamp'])` to see resource timelines).

Be concrete: cite resource names and connection weights from `abstract_sna`'s output, not generalities."""
    return [UserMessage(preamble + body + path_tip_footer(log_path))]
