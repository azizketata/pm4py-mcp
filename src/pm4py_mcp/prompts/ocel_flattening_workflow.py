"""Prompt: ``/ocel_flattening_workflow`` — compare object-type perspectives of an OCEL."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="ocel_flattening_workflow",
    title="OCEL flattening workflow",
    description="Compare each object type's perspective on an OCEL by flattening and abstracting per-type.",
)
def ocel_flattening_workflow(ocel_path: str) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Investigate the OCEL at `{ocel_path}` by comparing object-type perspectives.

Steps:
1. `load_ocel(path="{ocel_path}")` → ocel_id.
2. `describe_ocel(ocel_id)` — object types, per-type event counts, time range.
3. For **each object type** listed:
   a. `abstract_ocel(ocel_id, object_type=<type>)` — textual description of that type's events.
   b. `flatten_ocel(ocel_id, object_type=<type>)` → log_id_<type>.
   c. `abstract_dfg(log_id_<type>)` — DFG narrative for that projection.
4. `abstract_ocdfg(ocel_id)` — object-centric DFG across all types.
5. `discover_oc_petri_net(ocel_id)` → ocpn_id.
6. `visualize_oc_petri_net(ocpn_id)` — see cross-type transitions.

Then report:
- **Per-type summaries**: how does each object type see this process differently?
- **Richness**: which object type has the most variants or the longest traces?
- **Cross-type synchronization**: which activities appear in multiple type-views? They're the multi-object transitions in the OCPN.
- **Recommendation**: which object type is the "primary analytic lens" for this process?"""
    return [UserMessage(preamble + body)]
