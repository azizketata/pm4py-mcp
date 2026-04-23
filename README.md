# pm4py-mcp

An AGPL-licensed, stdio-first **Model Context Protocol** server that wraps [PM4Py](https://github.com/process-intelligence-solutions/pm4py) behind a small handle-based tool surface — making research-grade process mining available to Claude and any MCP-capable agent, locally and on open standards (XES, BPMN, PNML; OCEL 2.0 coming in Phase 2).

> **Status:** Phase 1 complete — `pm4py-mcp 0.1.0` ships 24 workflow-shaped tools spanning I/O, discovery, conformance, filtering, statistics, and visualization. Installable via `uvx pm4py-mcp`.

## Why

No open-source MCP server for process mining exists today. Celonis, SAP Signavio, and Microsoft Power Automate Process Mining all ship closed, SaaS-bound equivalents. `pm4py-mcp` fills the open, local, Python-native quadrant: event logs never leave the machine, algorithms are research-grade (Inductive Miner variants, alignments, POWL, OCEL 2.0), and the server composes cleanly into LangGraph / CrewAI / AutoGen crews.

## Install

### Prerequisites

- **Python 3.10–3.13** via [`uv`](https://docs.astral.sh/uv/)
- **Graphviz** — `dot` must be on PATH for visualization tools.
  - Windows: `winget install Graphviz.Graphviz`
  - macOS: `brew install graphviz`
  - Ubuntu: `sudo apt install graphviz`

### Claude Desktop / Claude Code configuration

MCP users configure servers via JSON, not via `pip install`. Add this to `claude_desktop_config.json` (or your Claude Code MCP settings):

```jsonc
{
  "mcpServers": {
    "pm4py": {
      "command": "uvx",
      "args": ["pm4py-mcp@latest"]
    }
  }
}
```

Quit Claude Desktop from the system tray (not just close the window) and relaunch. The server auto-downloads on first use.

## Walking example

With the server configured, start a new Claude chat and try:

> "Load the log at `<path>/examples/running-example.xes`. Describe it. Discover a Petri net with 0.2 noise threshold. Check conformance with token replay. Show me the diagram."

Claude will chain `load_event_log` → `describe_log` → `discover_petri_net` → `conformance_token_replay` → `visualize_petri_net`, returning an inline Petri-net PNG plus the fitness number and absolute file paths for the PNG + SVG. The [bundled example log](examples/running-example.xes) is an 8-case hospital-admission process with two variants.

## Tool catalog (Phase 1 — 24 tools)

All tools accept a handle (`log_id`, `petri_id`, etc.) or — for `load_event_log` — a file path. None returns the log itself; responses are always compact summaries plus new handles.

### I/O and workspace (4)
| Tool | Purpose |
|---|---|
| `load_event_log(path, format?, *_key?)` | Read XES / CSV / Parquet; returns `log_id` + summary. |
| `describe_log(log_id)` | Recompute the summary for a loaded log. |
| `export_log(log_id, format, path)` | Write XES or CSV back out. |
| `list_workspace()` | Enumerate derived artifacts in `~/.pm4py-mcp/workspace/`. |

### Statistics (4)
| Tool | Purpose |
|---|---|
| `get_variants(log_id, top_k)` | Most-common trace variants and counts. |
| `get_start_end_activities(log_id)` | First/last activity frequency dicts. |
| `get_case_durations(log_id)` | Min/max/mean/median + p50/p75/p90/p95/p99. |
| `get_cycle_time(log_id)` | Average inter-completion delay. |

### Discovery (4)
| Tool | Purpose |
|---|---|
| `discover_dfg(log_id)` | Directly-follows graph. |
| `discover_petri_net(log_id, algorithm, noise_threshold)` | Inductive / Heuristics / Alpha miner. |
| `discover_process_tree(log_id, noise_threshold)` | Process tree via Inductive Miner. |
| `discover_bpmn(log_id, noise_threshold)` | BPMN via Inductive Miner + conversion. |

### Conformance (2)
| Tool | Purpose |
|---|---|
| `conformance_token_replay(log_id, petri_id)` | Fast token-based fitness check. |
| `conformance_alignments(log_id, petri_id, multi_processing?)` | Alignment-based fitness. Async; emits progress for long runs. |

### Filtering (5)
All filter tools mint a **new** `log_id` — the original is untouched, so filter chains keep every intermediate handle.

| Tool | Purpose |
|---|---|
| `filter_variants(log_id, top_k \| variants, retain)` | Keep/drop by variant. |
| `filter_time_range(log_id, start, end, mode)` | ISO-8601 time window with 7 mode options. |
| `filter_attribute_values(log_id, attribute, values, retain, level)` | Event- or case-level attribute filter. |
| `filter_case_size(log_id, min_size, max_size)` | By event count per case. |
| `filter_case_performance(log_id, min_seconds, max_seconds)` | By end-to-end case duration. |

### Visualization (4)
Each viz tool saves **both PNG and SVG** to `~/.pm4py-mcp/workspace/`, returns a caption with absolute paths, and embeds the PNG inline when it fits under ~700 KB.

| Tool | Purpose |
|---|---|
| `visualize_petri_net(petri_id)` | Render a Petri net. |
| `visualize_dfg(dfg_id)` | Render a DFG. |
| `visualize_process_tree(tree_id)` | Render a process tree. |
| `visualize_bpmn(bpmn_id)` | Render a BPMN diagram. |

### Health check (1)
| Tool | Purpose |
|---|---|
| `ping()` | Returns `pong pm4py-mcp <version>`. |

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Walking skeleton: packaging, `ping` tool, CI test pyramid | ✅ shipped (0.0.1) |
| 1 | Core traditional-log toolkit: load / discover / conform / filter / visualize | ✅ shipped (0.1.0) |
| 2 | OCEL 2.0 namespace + advanced analytics (DECLARE, log skeleton, POWL) | planned |
| 3 | Agentic layer: textual abstractions, prompt library, DuckDB SQL, reports | planned |
| 4 | Hardening: Streamable HTTP, sandboxed `exec_python`, connectors, `.mcpb` bundle | planned |

See [Roadmap of development.pdf](Roadmap%20of%20development.pdf) for the architectural rationale.

## Architecture highlights

- **Handle-based state.** Event logs (10 MB – 1 GB DataFrames) stay server-side in an LRU `LogRegistry` (8 entries, 1-hour TTL). Tools exchange short `log_id` / `petri_id` / `bpmn_id` strings — never the logs themselves. Claude Desktop's ~1 MB response cap makes this mandatory.
- **Dual-channel visualizations.** Every render tool writes both PNG and SVG to the workspace, returns text + absolute paths, and attaches inline PNG only when it fits under ~700 KB.
- **Tools raise exceptions, never return error strings.** FastMCP converts raised exceptions into `isError=true` responses the LLM can recover from.
- **Long-running tools emit progress** via `ctx.report_progress` — alignments on a 500 MB log can exceed five minutes and need client timeout resets.
- **OCEL 2.0 gets a parallel namespace** (Phase 2). Object-centric logs won't overload existing tools; a `flatten_ocel(ocel_id, object_type) → log_id` bridge will keep them composable.
- **Tool surface stays small.** ~15–25 workflow-shaped verbs — not 1:1 with PM4Py's ~200-function API.

## License

**AGPL-3.0-or-later**, matching PM4Py's upstream license. Contributions require a DCO sign-off (`git commit -s`); no CLA.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, testing instructions, and architectural guardrails. Issues and discussions are open at <https://github.com/azizketata/pm4py-mcp>.
