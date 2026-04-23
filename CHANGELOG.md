# Changelog

All notable changes to `pm4py-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - TBD

Phase 2 Part 1 — **OCEL 2.0 support.** 12 new tools bring the total surface to **36 tools**. This is the decisive differentiator: no commercial MCP supports OCEL 2.0 (object-centric event logs). Phase 2 Part 2 (advanced discovery — DECLARE, POWL, log skeleton, organizational mining, conversions, simulation, advanced viz) defers to a separate 0.3.0 plan.

### Added

**OCEL 2.0 I/O + workspace (4 tools)**
- `load_ocel(path)` — auto-dispatches JSON-OCEL (`.jsonocel` / `.json`), XML-OCEL (`.xmlocel` / `.xml`), and SQLite-OCEL (`.sqlite`). Detects missing `pyarrow` for relational OCELs and raises `OptionalDepMissing` with the `pm4py-mcp[ocel]` install hint.
- `describe_ocel(ocel_id)` — compact summary: event/object counts, object types (capped to 20), events-per-object-type (top 10), activities preview, time range.
- `flatten_ocel(ocel_id, object_type)` — **the Phase 2 composability bridge.** Projects an OCEL onto a single object type and returns a traditional `log_id` that composes with every Phase 1 tool (discover, conform, filter, visualize). This single tool is what lets pm4py-mcp offer object-centric process mining without duplicating the entire Phase 1 surface.
- `export_ocel(ocel_id, format, path)` — JSON-OCEL / XML-OCEL / SQLite output. Bare filenames land in the workspace.

**OCEL discovery (2 tools)**
- `discover_ocdfg(ocel_id)` — object-centric directly-follows graph. Returns an `ocdfg_id` plus per-object-type edge counts + activity totals.
- `discover_oc_petri_net(ocel_id, variant)` — object-centric Petri net. `variant` ∈ `{"im", "imd"}`; returns an `ocpn_id` plus per-object-type (places, transitions, arcs) counts.

**OCEL visualization (2 tools)**
- `visualize_ocdfg(ocdfg_id)` — dual-channel PNG + SVG render with per-object-type colored edges (orders, items, deliveries each in their own color).
- `visualize_oc_petri_net(ocpn_id)` — dual-channel OCPN render showing cross-type object flows through shared transitions.

**OCEL filtering (4 tools — aggressively consolidated)**
These 4 tools wrap 7 separate PM4Py filter functions via `level` / `strategy` dispatch. Every filter mints a fresh `ocel_id` and returns both event AND object counts before/after.
- `filter_ocel_time_range(ocel_id, start, end)` — reuses the ISO-8601-to-pm4py timestamp normalizer extracted from Phase 1.
- `filter_ocel_attribute(ocel_id, attribute, values, level, retain)` — `level` ∈ `{"event", "object"}` dispatches to `pm4py.filter_ocel_event_attribute` / `filter_ocel_object_attribute`.
- `filter_ocel_object_types(ocel_id, types, retain)` — keep or drop entire object types.
- `filter_ocel_cc(ocel_id, strategy, value, retain)` — connected-component filtering with `strategy` ∈ `{"activity", "object", "otype", "length"}`. For `"length"`, `value` is `[min, max]`; for the others, `value` is a string.

**Infrastructure**
- Registry extended with 3 new kinds (`ocel`, `ocdfg`, `ocpn`) and prefixes (`ocel-`, `ocdfg-`, `ocpn-`).
- `OcelSummary`, `OcelExportResult`, `OcelFilterResult` dataclasses in `models.py`.
- `OptionalDepMissing` exception for missing optional dependencies (e.g., `pyarrow` for relational OCEL).
- `src/pm4py_mcp/_time.py` — `normalize_datetime` extracted to a shared module, reused by Phase 1 `filter_time_range` and Phase 2 `filter_ocel_time_range`.
- `examples/order-management.jsonocel` — 3.7 KB synthetic OCEL with 3 object types (order, item, delivery), 10 events, 8 objects, 16 relations.
- `scripts/generate_example_ocel.py` — regenerates the bundled OCEL deterministically.
- End-to-end OCEL workflow test in [tests/test_workflow_ocel_stdio.py](tests/test_workflow_ocel_stdio.py): load → describe → flatten → **Phase 1 discover_petri_net on the flattened log** → filter → export, all over a real stdio subprocess.

### Requires

- **`[ocel]` extra** (`pip install 'pm4py-mcp[ocel]'` or `uv sync --extra ocel`) is only needed for **relational (parquet-backed)** OCELs. JSON-OCEL, XML-OCEL, and SQLite-OCEL work without any additional dependencies.
- **Graphviz** — same system binary as Phase 1. OCEL visualizations use the same Graphviz backend (`save_vis_ocdfg`, `save_vis_ocpn`).

### Fixed (during Phase 2)

- OCPN viz caption previously reported "0 places, 0 arcs" because `OCPetriNet["places"]` returned empty dict instead of the flat set (attribute access works, dict access doesn't). `visualize_oc_petri_net` now computes totals from the authoritative `petri_nets` sub-dict.

### Design note — consolidation over mirroring

PM4Py exposes 7 separate OCEL filter functions and 2 attribute-filter functions. Phase 2 wraps them into **4** tools using `strategy` / `level` params. This was an explicit choice at planning time: smaller tool surface ⇒ smaller prompt footprint for the LLM ⇒ cleaner disambiguation between similar verbs. The consolidation keeps the total 0.2.0 tool count at 36 instead of 40+.

### Known limitations

- PM4Py's `filter_ocel_cc_*` family is marked experimental — expect occasional edge-case failures on malformed OCELs. Pinned `pm4py>=2.7,<3` to insulate against API drift.
- No OCEL-specific conformance tools in 0.2.0 — use `flatten_ocel` to project onto a single object type, then Phase 1 `conformance_*` tools.
- Advanced discovery (DECLARE, log skeleton, temporal profile, POWL, organizational mining), model conversions, simulation, and advanced visualizations (dotted chart, performance spectrum) are deferred to 0.3.0.

## [0.1.0] - TBD

Phase 1 — core traditional-log toolkit. 23 new tools bring the total surface to **24 tools** covering the minimum-viable PM4Py slice that a process-mining analyst can drive from Claude.

### Added

**I/O and workspace (4 tools)**
- `load_event_log(path, format?, case_id_key?, activity_key?, timestamp_key?)` — XES, CSV, Parquet; emits `ctx.report_progress` for files > 10 MB.
- `describe_log(log_id)` — compact summary: case/event counts, activities preview, time range, top 5 variants.
- `export_log(log_id, format, path)` — XES or CSV output. Bare filenames land in the workspace.
- `list_workspace()` — enumerate derived artifacts.

**Statistics (4 tools)**
- `get_variants(log_id, top_k)` — top-k trace variants with counts + total variant count.
- `get_start_end_activities(log_id)` — activity frequency dicts.
- `get_case_durations(log_id)` — min/max/mean/median + p50/p75/p90/p95/p99. Full per-case list never returned.
- `get_cycle_time(log_id)` — average inter-completion delay in seconds.

**Discovery (4 tools)**
- `discover_dfg(log_id)` — returns `dfg_id` + arc/start/end counts.
- `discover_petri_net(log_id, algorithm, noise_threshold)` — dispatches on `{inductive, heuristics, alpha}`.
- `discover_process_tree(log_id, noise_threshold)` — Inductive Miner, returns `tree_id` + structural depth/size.
- `discover_bpmn(log_id, noise_threshold)` — Inductive Miner + BPMN conversion.

**Conformance (2 tools)**
- `conformance_token_replay(log_id, petri_id)` — token-based replay; aggregates into `num_fit_cases` + `mean_trace_fitness`.
- `conformance_alignments(log_id, petri_id, multi_processing)` — alignment-based; async with progress reporting for long runs. `multi_processing` defaults to `False` (Windows-safe).

**Filtering (5 tools)**
All filter tools mint a fresh `log_id`, leaving the source log intact. Returns include `num_cases_before/after` and `num_events_before/after` so chains stay readable.
- `filter_variants(log_id, top_k | variants, retain)` — by variant (top-k or explicit list).
- `filter_time_range(log_id, start, end, mode)` — seven modes (events / traces_contained / traces_intersecting / starting_in / completing_in + exclude variants). Normalizes ISO-8601 `T` separator to pm4py's expected `' '` format.
- `filter_attribute_values(log_id, attribute, values, retain, level)` — event or case level. `level` is passed explicitly to avoid pm4py's deprecation warning.
- `filter_case_size(log_id, min_size, max_size)` — by event count.
- `filter_case_performance(log_id, min_seconds, max_seconds)` — by elapsed time.

**Visualization (4 tools)**
Each saves both PNG and SVG to `~/.pm4py-mcp/workspace/`, returns a caption with absolute paths, and embeds the PNG inline when ≤ 700 KB. Uses `@mcp.tool(structured_output=False)` to return the mixed `[text, Image]` content list.
- `visualize_petri_net(petri_id)`
- `visualize_dfg(dfg_id)`
- `visualize_process_tree(tree_id)`
- `visualize_bpmn(bpmn_id)`

**Infrastructure**
- `LogRegistry` — in-memory LRU (8 entries) + TTL (1 hour) artifact store, handle-prefixed per kind (`log-`, `pn-`, `pt-`, `bpmn-`, `dfg-`).
- Workspace directory resolution — `~/.pm4py-mcp/workspace/` by default, overrideable via `PM4PY_MCP_WORKSPACE` env var.
- `save_dual_channel` viz helper — saves PNG + SVG, budgets inline attachment.
- Custom exception taxonomy: `HandleNotFound`, `InvalidKind`, `UnsupportedFormat`, `WorkspaceError`, `GraphvizMissing`.
- `examples/running-example.xes` — 8-case hospital-admission log for demos and CI smoke tests.
- `scripts/generate_example_log.py` — regenerate the example log deterministically.

### Requires

- **Graphviz system binary** (`dot`) must be on PATH for any `visualize_*` tool. Missing binary raises `GraphvizMissing` with an installation hint.
  - Windows: `winget install Graphviz.Graphviz`
  - macOS: `brew install graphviz`
  - Ubuntu: `sudo apt install graphviz`

### Fixed (during Phase 0 → Phase 1)

- `astral-sh/setup-uv@v8` was unresolvable in GitHub Actions; pinned to `@v8.1.0` (immutable patch tag).
- `pm4py.filter_time_range` rejects ISO-8601 `T` separator; `filter_time_range` now normalizes inputs via `pd.to_datetime`.
- FastMCP's default output-schema generation fails to serialize `Image` objects; all 4 visualization tools opt out with `@mcp.tool(structured_output=False)`.

### Known limitations

- No per-trace detail returned from conformance tools — Phase 3 will add `render_report` with Markdown + embedded CSVs.
- `conformance_alignments` emits progress only at start and end of the per-trace loop, not per-trace. Adequate for client timeout resets; finer-grained progress deferred.
- OCEL 2.0, textual abstractions, and the agentic prompt library are Phase 2–3 work.

## [0.0.1] - 2026-04-23

First PyPI release claiming the `pm4py-mcp` name. No user-facing functionality beyond the `ping` health-check tool — this is the "walking skeleton" that proves the end-to-end pipeline from a git tag through Trusted Publishing to Claude Desktop.

### Added

- Governance files: `LICENSE` (AGPL-3.0-or-later), `CONTRIBUTING.md` (with DCO requirement), `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`.
- Package scaffolding: `pyproject.toml` using hatchling, `src/pm4py_mcp/` layout.
- Single `ping` tool served over stdio via FastMCP.
- Four-layer testing pyramid: unit, in-process `ClientSession`, stdio subprocess, MCP Inspector CLI (nightly).
- CI matrix: Python 3.10–3.13 × Ubuntu / macOS / Windows.
- PyPI Trusted Publishing workflow: TestPyPI for pre-release tags, PyPI for release tags.

[Unreleased]: https://github.com/azizketata/pm4py-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.2.0
[0.1.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.1.0
[0.0.1]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.0.1
