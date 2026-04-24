"""Prompt: ``/executive_summary`` — consolidate analysis into a render_report call."""

from __future__ import annotations

from mcp.server.fastmcp.prompts.base import UserMessage

from pm4py_mcp.prompts._shared import maybe_prepend_context, path_tip_footer
from pm4py_mcp.server import mcp


@mcp.prompt(
    name="executive_summary",
    title="Executive summary",
    description="Consolidate the session's findings into a rendered Markdown report.",
)
def executive_summary(log_id_or_path: str, title: str) -> list[UserMessage]:
    preamble = maybe_prepend_context()
    body = f"""Produce an executive-grade summary titled **"{title}"** for the log at `{log_id_or_path}`.

Steps:
1. If `{log_id_or_path}` looks like a file path, `load_event_log(path="{log_id_or_path}")` first.
   Otherwise treat it as an existing `log_id`.
2. Summarize via `describe_log` + `abstract_log_features` + `abstract_variants` — know the shape of the log.
3. If a Petri net and conformance report aren't already in the session, build them: `discover_petri_net` → `conformance_token_replay` → `visualize_petri_net`.
4. When you have enough to write a narrative, call `render_report` with:
   - `title="{title}"`
   - `findings=<your concise Markdown narrative>`
   - `artifact_paths=<list of PNG/SVG/CSV paths you've accumulated this session>`

Rules for the narrative:
- **Concise**: each finding in one sentence.
- **Concrete**: cite numbers (case count, fitness, percentages).
- **Actionable**: end with 2-3 recommended next steps.
- Assume the reader is a non-technical executive."""
    # executive_summary takes a polymorphic log_id_or_path; the footer is still useful
    # when the argument is a path rather than a log-* handle.
    return [UserMessage(preamble + body + path_tip_footer(log_id_or_path))]
