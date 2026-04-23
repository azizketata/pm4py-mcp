# pm4py-mcp

An AGPL-licensed, stdio-first **Model Context Protocol** server that wraps [PM4Py](https://github.com/process-intelligence-solutions/pm4py) behind handle-based tools — making research-grade process mining available to Claude and any MCP-capable agent, locally and on open standards (XES, OCEL 2.0, BPMN, PNML).

> **Status:** Phase 0 — planning / walking skeleton. Not yet published to PyPI.

## Why

No open-source MCP server for process mining exists today. Celonis, SAP Signavio, and Microsoft Power Automate Process Mining all ship closed, SaaS-bound equivalents. `pm4py-mcp` fills the open, local, Python-native quadrant: event logs never leave the machine, algorithms are research-grade (Inductive Miner variants, alignments, POWL, OCEL 2.0), and the server composes cleanly into LangGraph / CrewAI / AutoGen crews.

## Planned usage (Phase 1)

Once published, the intended installation path is via `uvx` rather than `pip install` — MCP users configure servers, they don't install them:

```jsonc
// claude_desktop_config.json
{
  "mcpServers": {
    "pm4py": {
      "command": "uvx",
      "args": ["pm4py-mcp@latest"]
    }
  }
}
```

Then in Claude:

> "Load sepsis.xes, discover a Petri net with 0.2 noise threshold, check conformance, and show me the diagram."

## Roadmap

| Phase | Scope | Effort |
|-------|-------|--------|
| 0 | Walking skeleton: packaging, `ping` tool, CI test pyramid | 1–2 weeks |
| 1 | Core traditional-log toolkit: load / discover / conform / filter / visualize | 3–4 weeks |
| 2 | OCEL 2.0 namespace + advanced analytics (DECLARE, log skeleton, POWL) | 3–4 weeks |
| 3 | Agentic layer: textual abstractions, prompt library, DuckDB SQL, reports | 4–6 weeks |
| 4 | Hardening: Streamable HTTP, sandboxed `exec_python`, connectors, `.mcpb` bundle | ongoing |

See [Roadmap of development.pdf](Roadmap%20of%20development.pdf) for the full architectural rationale.

## Architecture highlights

- **Handle-based state.** Event logs (10 MB – 1 GB DataFrames) are kept server-side in an LRU `LogRegistry`; tools exchange short `log_id` strings, never the logs themselves. Claude Desktop's ~1 MB response cap makes this mandatory.
- **Dual-channel visualizations.** Every render tool writes both PNG and SVG to the workspace, returns text + absolute paths, and only attaches inline PNG when it fits under ~700 KB.
- **OCEL 2.0 gets a parallel namespace.** `ocel_*` tools sit alongside traditional-log tools; a `flatten_ocel(ocel_id, object_type) → log_id` bridge keeps them composable.
- **Tool surface stays small.** ~15–25 workflow-shaped verbs (load, describe, discover, filter, conform, visualize, stats, export) — not 1:1 with PM4Py's ~200-function API.

## License

**AGPL-3.0-or-later**, matching PM4Py's upstream license. Contributions require a DCO sign-off (`git commit -s`); no CLA.

## Contributing

This repository is in pre-release scaffolding. Issues and discussions will open once Phase 0 deliverables land.
