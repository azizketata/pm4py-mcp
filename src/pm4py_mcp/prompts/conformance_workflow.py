"""Prompt: ``/conformance_workflow`` — load, discover, replay, align, explain."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="conformance_workflow",
    title="Conformance workflow",
    description="Discover a Petri net and compare token-replay vs alignments fitness.",
)
def conformance_workflow(
    log_path: str,
    noise_threshold: float = 0.2,
) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Run a conformance investigation on the log at `{log_path}` with noise_threshold={noise_threshold}.

Steps:
1. `load_event_log(path="{log_path}")` → log_id.
2. `describe_log(log_id)` — note case count and activity set.
3. `discover_petri_net(log_id, algorithm="inductive", noise_threshold={noise_threshold})` → petri_id.
4. `abstract_petri_net(petri_id)` — read the model description so you can narrate structure.
5. `conformance_token_replay(log_id, petri_id)` — capture mean fitness and fit-case count.
6. `conformance_alignments(log_id, petri_id)` — capture mean fitness (alignments are stricter).
7. `abstract_variants(log_id)` — see which variants likely drive any unfitness.
8. `visualize_petri_net(petri_id)` — attach the rendered diagram.

Then write a conformance report:
- Mean fitness under **token replay** vs **alignments** — are they similar or does alignments reveal deviations token replay missed?
- How many of N cases fit perfectly?
- Name the specific variants that most likely contribute to deviations.
- Is `noise_threshold={noise_threshold}` appropriate for this log, or should we tighten/loosen it?"""
    return [UserMessage(preamble + body)]
