# Changelog

All notable changes to `pm4py-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/azizketata/pm4py-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.1.0
[0.0.1]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.0.1
