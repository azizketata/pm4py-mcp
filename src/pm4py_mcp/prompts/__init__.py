"""Phase 3 — curated prompt library.

Each submodule registers one ``@mcp.prompt`` slash command that seeds a
canonical process-mining investigation. Importing this package is a
side-effect operation: the prompts get attached to the shared ``mcp``
singleton in ``pm4py_mcp.server``.

Six prompts in 0.3.0:
- conformance_workflow      — load + discover + replay + alignments + explain
- bottleneck_analysis       — find slowest variants + bottleneck edges
- variant_exploration       — top-k variants, drill into the dominant one
- new_log_onboarding        — 2-minute first-impression summary
- ocel_flattening_workflow  — compare object-type perspectives of an OCEL
- executive_summary         — consolidate findings into a render_report call
"""

from __future__ import annotations

from pm4py_mcp.prompts import (  # noqa: F401
    bottleneck_analysis,
    conformance_workflow,
    executive_summary,
    new_log_onboarding,
    ocel_flattening_workflow,
    organizational_analysis,
    variant_exploration,
)

__all__: list[str] = []
