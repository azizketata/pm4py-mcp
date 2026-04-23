# CLAUDE.md

Context for Claude Code when working in this repository.

## Project

`pm4py-mcp` — the first open-source Model Context Protocol server for process mining. Wraps [PM4Py](https://github.com/process-intelligence-solutions/pm4py) behind a small, workflow-shaped tool surface so MCP-capable agents (Claude Desktop, Claude Code, LangGraph, CrewAI, AutoGen) can run research-grade process mining on local event logs.

The authoritative design document is `Roadmap of development.pdf` at the repo root. Read it before proposing architectural changes.

## Current phase

**Phase 0 — Foundations.** Only scaffolding and governance files exist. No Python code, no PyPI release, no tools implemented yet.

## Locked architectural decisions

Do not revisit these without explicit user discussion — they cascade through every phase:

1. **Handle-based, in-memory state.** Tools accept either a file path (first call) or a `log_id` handle (subsequent calls) and return a new handle plus a tiny summary. State lives in a server-side LRU `LogRegistry` (~8 logs, 1-hour TTL). Never return event logs themselves — Claude Desktop enforces a ~1 MB response ceiling.
2. **Dual-channel visualizations.** Every render tool saves both PNG and SVG to the workspace, returns text + absolute paths, and attaches an `ImageContent` block only when a downscaled PNG fits under ~700 KB.
3. **FastMCP SDK, pinned `mcp>=1.20,<2`.** Stdio transport only in v1. Streamable HTTP is a Phase 4 addition. Do not build SSE.
4. **OCEL 2.0 gets a parallel `ocel_*` namespace**, not overloaded tools. `flatten_ocel(ocel_id, object_type) → log_id` is the composability bridge.
5. **License: AGPL-3.0-or-later.** Matches PM4Py upstream. DCO sign-off required on commits; no CLA.
6. **Packaging: hatchling + `src/pm4py_mcp/` + PyPI Trusted Publishing.** Primary install channel is `uvx pm4py-mcp`, not `pip install`.
7. **Tool surface ~15–25 workflow verbs, not 1:1 with PM4Py's ~200 functions.** Organize as verbs: load, describe, discover, filter, conform, visualize, stats, export.

## Conventions

- **Python:** 3.10–3.13 (intersection of MCP SDK 3.10+ and PM4Py 3.9–3.14).
- **Tools raise exceptions**, never return error strings — the SDK converts raised exceptions into `isError=true` responses the LLM can recover from.
- **Long-running tools must emit progress** via `ctx.report_progress` — alignments on a 500 MB log can exceed five minutes and need timeout resets.
- **Workspace directory:** `~/.pm4py-mcp/workspace` for derived artifacts. State does not persist across client restarts (document this).

## Repository layout (planned)

```
pm4py-mcp/
├── src/pm4py_mcp/          # server, tools, registry (Phase 0+)
├── tests/                  # pytest unit + in-process ClientSession + stdio subprocess + Inspector CLI
├── examples/               # langgraph_analyst_crew.py, crewai_engineer_analyst.py, autogen_pm_team.py
├── docs/                   # mkdocs-material source
├── pyproject.toml          # hatchling, extras: [ocel], [llm], [dev]
├── CLAUDE.md               # this file
├── README.md
├── LICENSE                 # AGPL-3.0-or-later
├── CONTRIBUTING.md         # with DCO requirement
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── CHANGELOG.md
```

None of the `src/` or `tests/` tree exists yet.

## What not to do

- Don't add `pip install` instructions to the README — users configure MCP servers via JSON, they don't install them.
- Don't wrap the full PM4Py API. Anti-pattern: "dumping 43 tools into the context window."
- Don't return event logs, DataFrames, or large binary blobs from tool responses. Always return handles + summaries + file paths.
- Don't overload tools to accept both traditional logs and OCEL — use the parallel namespace.
- Don't commit large sample logs (BPI Challenge sets are hundreds of MB). Ship a `scripts/download_benchmark_logs.py` instead.
