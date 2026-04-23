# pm4py-mcp

An AGPL-licensed, stdio-first **Model Context Protocol** server that wraps [PM4Py](https://github.com/process-intelligence-solutions/pm4py) behind a small handle-based tool surface — making research-grade process mining available to Claude and any MCP-capable agent, locally and on open standards (XES, **OCEL 2.0**, BPMN, PNML).

> **Status:** Phase 2 Part 1 shipped — `pm4py-mcp 0.2.0` ships **36 workflow-shaped tools** spanning I/O, discovery, conformance, filtering, statistics, visualization, **and OCEL 2.0 object-centric process mining**. Installable via `uvx pm4py-mcp`.

**Today** — load XES / CSV / Parquet logs **or OCEL 2.0 (JSON / XML / SQLite)**, discover Petri nets / process trees / BPMN / DFGs / **object-centric Petri nets / OC-DFGs**, run token-replay or alignment conformance, filter chains that mint fresh handles across both traditional and object-centric logs, and render every model inline as PNG + SVG. 36 natural-language tools, fully local, nothing leaves your machine.

**Next (0.3.0)** — advanced discovery (DECLARE, POWL, log skeleton, organizational mining), model conversions (Petri ↔ BPMN ↔ Process Tree ↔ POWL), simulation (`play_out`), dotted chart + performance spectrum, LLM-aware textual abstractions, and a curated prompt library for canonical PM investigations. Team deployment via Streamable HTTP lands in Phase 4.

## Why

No open-source MCP server for process mining exists today. Celonis, SAP Signavio, and Microsoft Power Automate Process Mining all ship closed, SaaS-bound equivalents — and **none of them support OCEL 2.0**. `pm4py-mcp` fills the open, local, Python-native quadrant: event logs never leave the machine, algorithms are research-grade (Inductive Miner variants, alignments, OCEL 2.0, object-centric Petri nets), and the server composes cleanly into LangGraph / CrewAI / AutoGen crews.

## Install

### Prerequisites

- **Python 3.10–3.13** via [`uv`](https://docs.astral.sh/uv/)
- **Graphviz** — `dot` must be on PATH for visualization tools.
  - Windows: `winget install Graphviz.Graphviz`
  - macOS: `brew install graphviz`
  - Ubuntu: `sudo apt install graphviz`
- **Optional `[ocel]` extra** — only needed for relational (parquet-backed) OCELs. `pip install 'pm4py-mcp[ocel]'` or `uvx --with 'pm4py-mcp[ocel]' pm4py-mcp`. JSON-OCEL, XML-OCEL, and SQLite-OCEL work without it.

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

Once the MCP client picks up the config, `pm4py` shows up as a connected server:

![pm4py connected in the MCP servers panel](docs/images/mcp-connected.png)

## Walking examples

### Traditional log — `examples/running-example.xes`

> "Load the log at `<path>/examples/running-example.xes`. Describe it. Discover a Petri net with 0.2 noise threshold. Check conformance with token replay. Show me the diagram."

Claude will chain `load_event_log` → `describe_log` → `discover_petri_net` → `conformance_token_replay` → `visualize_petri_net`, returning an inline Petri-net PNG plus the fitness number and absolute file paths for the PNG + SVG. The [bundled example log](examples/running-example.xes) is an 8-case hospital-admission process with two variants:

![Discovered Petri net: register -> triage -> (consult | treat) -> discharge](docs/images/petri-net-example.png)

Token-replay conformance against this model returns `mean_trace_fitness = 1.0` (8/8 fit cases).

### Object-centric log — `examples/order-management.jsonocel`

> "Load `<path>/examples/order-management.jsonocel`. What object types are in it? Flatten it by `order` and discover a Petri net from that view. Now discover the object-centric Petri net across all object types and show me the diagram."

Claude chains `load_ocel` → `describe_ocel` → `flatten_ocel(object_type="order")` → `discover_petri_net` (Phase 1 tool on the flattened log) → `discover_oc_petri_net` → `visualize_oc_petri_net`. The OCPN shows three color-separated flows (order, item, delivery) sharing the `Pick Item` and `Ship` transitions — multi-object interactions that a flattened log would lose:

![Object-centric Petri net across order, item, delivery object types](docs/images/ocel-ocpn-example.png)

The [bundled OCEL](examples/order-management.jsonocel) is a 3.7 KB synthetic order-management process with 3 object types (order, item, delivery), 10 events, 8 objects.

## Tool catalog (Phase 1 + 2 Part 1 — 36 tools)

All tools accept a handle (`log_id`, `petri_id`, `ocel_id`, …) or — for `load_*` tools — a file path. None returns the log itself; responses are always compact summaries plus new handles.

### Traditional log I/O (4)
| Tool | Purpose |
|---|---|
| `load_event_log(path, format?, *_key?)` | Read XES / CSV / Parquet; returns `log_id` + summary. |
| `describe_log(log_id)` | Recompute the summary for a loaded log. |
| `export_log(log_id, format, path)` | Write XES or CSV back out. |
| `list_workspace()` | Enumerate derived artifacts in `~/.pm4py-mcp/workspace/`. |

### OCEL 2.0 I/O + the flatten bridge (4)
| Tool | Purpose |
|---|---|
| `load_ocel(path)` | Read JSON-OCEL / XML-OCEL / SQLite-OCEL; returns `ocel_id` + per-type summary. |
| `describe_ocel(ocel_id)` | Object types, per-type event counts, activities preview, time range. |
| `flatten_ocel(ocel_id, object_type)` | **Composability bridge** — projects to a traditional `log_id` usable by every Phase 1 tool. |
| `export_ocel(ocel_id, format, path)` | Write JSON-OCEL / XML-OCEL / SQLite back out. |

### Statistics (4)
| Tool | Purpose |
|---|---|
| `get_variants(log_id, top_k)` | Most-common trace variants and counts. |
| `get_start_end_activities(log_id)` | First/last activity frequency dicts. |
| `get_case_durations(log_id)` | Min/max/mean/median + p50/p75/p90/p95/p99. |
| `get_cycle_time(log_id)` | Average inter-completion delay. |

### Traditional discovery (4)
| Tool | Purpose |
|---|---|
| `discover_dfg(log_id)` | Directly-follows graph. |
| `discover_petri_net(log_id, algorithm, noise_threshold)` | Inductive / Heuristics / Alpha miner. |
| `discover_process_tree(log_id, noise_threshold)` | Process tree via Inductive Miner. |
| `discover_bpmn(log_id, noise_threshold)` | BPMN via Inductive Miner + conversion. |

### OCEL discovery (2)
| Tool | Purpose |
|---|---|
| `discover_ocdfg(ocel_id)` | Object-centric directly-follows graph. |
| `discover_oc_petri_net(ocel_id, variant)` | Object-centric Petri net. `variant` ∈ `{im, imd}`. |

### Conformance (2)
| Tool | Purpose |
|---|---|
| `conformance_token_replay(log_id, petri_id)` | Fast token-based fitness check. |
| `conformance_alignments(log_id, petri_id, multi_processing?)` | Alignment-based fitness. Async; emits progress for long runs. |

### Traditional filtering (5)
All filter tools mint a **new** `log_id` — the original is untouched, so filter chains keep every intermediate handle.

| Tool | Purpose |
|---|---|
| `filter_variants(log_id, top_k \| variants, retain)` | Keep/drop by variant. |
| `filter_time_range(log_id, start, end, mode)` | ISO-8601 time window with 7 mode options. |
| `filter_attribute_values(log_id, attribute, values, retain, level)` | Event- or case-level attribute filter. |
| `filter_case_size(log_id, min_size, max_size)` | By event count per case. |
| `filter_case_performance(log_id, min_seconds, max_seconds)` | By end-to-end case duration. |

### OCEL filtering (4 — consolidated)
Four tools wrap 7 PM4Py filter functions via `level` / `strategy` dispatch. Each mints a fresh `ocel_id`.

| Tool | Purpose |
|---|---|
| `filter_ocel_time_range(ocel_id, start, end)` | Time-window filter; accepts ISO-8601. |
| `filter_ocel_attribute(ocel_id, attribute, values, level, retain)` | `level` ∈ `{event, object}`. |
| `filter_ocel_object_types(ocel_id, types, retain)` | Keep or drop whole object types. |
| `filter_ocel_cc(ocel_id, strategy, value, retain)` | Connected-component filter. `strategy` ∈ `{activity, object, otype, length}`. |

### Traditional visualization (4)
Each viz tool saves **both PNG and SVG** to `~/.pm4py-mcp/workspace/`, returns a caption with absolute paths, and embeds the PNG inline when it fits under ~700 KB.

| Tool | Purpose |
|---|---|
| `visualize_petri_net(petri_id)` | Render a Petri net. |
| `visualize_dfg(dfg_id)` | Render a DFG. |
| `visualize_process_tree(tree_id)` | Render a process tree. |
| `visualize_bpmn(bpmn_id)` | Render a BPMN diagram. |

### OCEL visualization (2)
| Tool | Purpose |
|---|---|
| `visualize_ocdfg(ocdfg_id)` | Render an OC-DFG — edges colored per object type. |
| `visualize_oc_petri_net(ocpn_id)` | Render an OCPN — per-type places and cross-type shared transitions. |

### Health check (1)
| Tool | Purpose |
|---|---|
| `ping()` | Returns `pong pm4py-mcp <version>`. |

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Walking skeleton: packaging, `ping` tool, CI test pyramid | ✅ shipped (0.0.1) |
| 1 | Core traditional-log toolkit: load / discover / conform / filter / visualize | ✅ shipped (0.1.0) |
| 2 Part 1 | OCEL 2.0 namespace + the flatten bridge | ✅ **shipped (0.2.0)** |
| 2 Part 2 | Advanced discovery (DECLARE, POWL, log skeleton, organizational mining), conversions, simulation, advanced viz | planned (0.3.0) |
| 3 | Agentic layer: textual abstractions, prompt library, DuckDB SQL, reports | planned |
| 4 | Hardening: Streamable HTTP, sandboxed `exec_python`, connectors, `.mcpb` bundle | planned |

See [Roadmap of development.pdf](Roadmap%20of%20development.pdf) for the architectural rationale.

## Architecture highlights

- **Handle-based state.** Event logs (10 MB – 1 GB) stay server-side in an LRU `LogRegistry` (8 entries, 1-hour TTL). Tools exchange short typed handles (`log-`, `pn-`, `bpmn-`, `pt-`, `dfg-`, `ocel-`, `ocdfg-`, `ocpn-`) — never the logs themselves. Claude Desktop's ~1 MB response cap makes this mandatory.
- **The flatten bridge.** `flatten_ocel(ocel_id, object_type) → log_id` is what makes the parallel OCEL namespace composable with the traditional-log namespace. Phase 2 didn't duplicate Phase 1's 20+ tools for OCEL; it exposed one tool that projects OCELs onto any object-type perspective and hands the result back into Phase 1.
- **Dual-channel visualizations.** Every render tool writes both PNG and SVG to the workspace, returns text + absolute paths, and attaches inline PNG only when it fits under ~700 KB.
- **Tools raise exceptions, never return error strings.** FastMCP converts raised exceptions into `isError=true` responses the LLM can recover from.
- **Long-running tools emit progress** via `ctx.report_progress` — alignments on a 500 MB log can exceed five minutes and need client timeout resets.
- **Aggressive consolidation over API-mirroring.** OCEL filtering wraps 7 PM4Py functions behind 4 tools via `strategy` / `level` dispatch; 4 CC variants share a single verb. Smaller tool surface → smaller prompt → cleaner LLM choices.
- **Tool surface stays focused.** 36 workflow-shaped verbs — not 1:1 with PM4Py's ~200-function API.

## License

**AGPL-3.0-or-later**, matching PM4Py's upstream license. Contributions require a DCO sign-off (`git commit -s`); no CLA.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, testing instructions, and architectural guardrails. Issues and discussions are open at <https://github.com/azizketata/pm4py-mcp>.
