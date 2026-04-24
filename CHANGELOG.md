# Changelog

All notable changes to `pm4py-mcp` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - TBD

Phase 2 Part 2 (second half) — **organizational mining + simulation + advanced visualization.** 9 new tools + 1 new prompt bring the total surface to **67 tools + 7 prompts**. 2 new registry kinds. After 0.4.1, Phase 2 Part 2 is complete.

### Added

**Organizational mining (5 tools)** — 1:1 discovery tools per-metric (not consolidated behind a `metric` parameter, per the OCEL-precedent choice). Each stores its result under a new registry kind with a `source_handle` breadcrumb pointing at the source `log_id`.

- `discover_handover_network(log_id, beta=0, resource_key="org:resource")` — edges represent direct work handoffs between resources within a case.
- `discover_working_together_network(log_id, resource_key="org:resource")` — undirected collaboration (same case participation).
- `discover_subcontracting_network(log_id, n=2, resource_key="org:resource")` — "A briefly hands to B and resumes" patterns.
- `discover_activity_based_resource_similarity(log_id, activity_key, resource_key)` — skill/role overlap via activity profiles.
- `discover_organizational_roles(log_id, activity_key, resource_key)` — clusters resources by activity sharing. Stores under a new `org_roles` kind; returns top-5 roles in the response with their activity + resource sets.

**Simulation (1 tool)**
- `simulate_log(model_id, num_traces=1000)` — wraps `pm4py.play_out`. Accepts `petri_net` (tuple) or `process_tree` handles; returns a fresh **`log_id`** (regular log kind) so the simulated output composes with every Phase 1 tool (`describe_log`, `abstract_variants`, `conformance_*`, filters). `source_handle` points back at the generating model. Caps `num_traces` at 10,000 to protect against runaway playouts on cyclic models. Handles the pm4py-internal parameter-name difference between Petri (`noTraces`) and process-tree (`num_traces`) playout variants transparently. Process-tree playout's case-id-less trace output is backfilled with synthetic `sim-case-{i}` IDs + timestamps so the simulated log has the columns Phase 1 tools expect.

**Advanced visualization (2 tools)** — matplotlib-backed, PNG-only. New parallel helper `src/pm4py_mcp/_matplotlib.py::save_matplotlib_png` keeps Graphviz's error handling clean in `viz.py`.
- `visualize_dotted_chart(log_id, attributes=None)` — time-vs-value scatter. Default `attributes=["concept:name", "time:timestamp"]`. Validates attribute presence in the log and fails fast with a helpful message listing available columns.
- `visualize_performance_spectrum(log_id, activities)` — duration-per-case across an ordered activity subset. `activities` required (no sensible default across all logs). Validates activity presence.

**Abstractions (1 tool)**
- `abstract_sna(sna_id, top_k=10)` — hand-written descriptor (pm4py has no `sna_to_descr`). Reports resource count, the top-k strongest connections by weight, and sink/source resources (no outgoing / no incoming edges). Works on any SNA handle regardless of which network-discovery tool produced it.

**Prompts (1 new)**
- `/organizational_analysis(log_path)` — canonical org-mining workflow: load → describe → handover + working-together networks + `abstract_sna` on each + organizational roles → narrate team structure, dominant handoffs, network sinks/sources, role clusters, bottleneck resources. Prerequisite: log must have an `org:resource` column; the prompt tells Claude to fail fast if absent.

### Infrastructure

- **2 new registry kinds**: `sna` (prefix `sna-`, used by all 4 network-discovery tools) and `org_roles` (prefix `role-`).
- **New module `src/pm4py_mcp/_matplotlib.py`** — PNG-only rendering helper parallel to `viz.py::save_dual_channel`. Separate module by design — Graphviz and matplotlib have genuinely different failure modes.
- **New tool modules** `src/pm4py_mcp/tools/org_mining.py` and `src/pm4py_mcp/tools/simulation.py` wired into `pm4py_mcp.tools.__init__` via the existing side-effect-import pattern.
- **New test fixture `tiny_log_with_resources()`** in `tests/fixtures.py` — the original `tiny_log` had no `org:resource` column; org-mining tests use the enriched version while Phase 1/2/3 tests are unchanged.

### Deferred (post-0.4.1)

- **`visualize_sna`** — pm4py renders SNA as pyvis HTML, which is dead weight for Claude clients. Bridge via NetworkX + matplotlib deferred to 0.5.0 or later when the output can be a first-class inline PNG.
- **`abstract_powl`** — pm4py upstream would need `powl_to_descr`; hand-writing is a research project.
- **`run_duckdb_sql`**, **`semantic_anomaly_detect`** — 0.5.0+.

### Design notes

- **5 separate org-mining tools, not 1 consolidated `discover_sna(metric)`.** Matches the OCEL-filter-style precedent of keeping distinct semantic functions as distinct tools; per-metric kwargs (`beta` for handover, `n` for subcontracting) stay first-class instead of hiding behind `**kwargs`.
- **`simulate_log` returns a regular `log` kind**, not a specialized `simulated_log` kind. That's the whole point — simulation output should be a first-class citizen that composes with every Phase 1 tool (`describe_log(simulated_id)`, `abstract_variants(simulated_id)`, etc.). This mirrors Phase 2's `flatten_ocel` design (OCEL → log_id composability bridge).

## [0.4.0] - TBD

Phase 2 Part 2 (first half) — **advanced discovery + model conversions + POWL visualization.** 9 new tools bring the total surface to **58 tools**. Unlocks the three Phase 3-deferred abstractions (`abstract_declare`, `abstract_log_skeleton`, `abstract_temporal_profile`) and introduces POWL and model-conversion workflows. 4 new registry kinds. Semver minor.

### Added

**Advanced discovery (4 tools)** — each stores its artifact under a new registry kind and records the source `log_id` as a lineage breadcrumb.
- `discover_declare(log_id, min_support_ratio?, min_confidence_ratio?)` — discovers a DECLARE model (17 constraint templates: response, precedence, succession, etc.). Returns `declare_id` + template/constraint counts + top-10 templates by constraint density.
- `discover_log_skeleton(log_id, noise_threshold=0.0)` — discovers the 6-family behavioral skeleton (equivalence, always_after, always_before, never_together, directly_follows, activ_freq). Returns `log_skeleton_id` + per-type constraint counts.
- `discover_powl(log_id)` — discovers a POWL (Partially Ordered Workflow Language) model. Returns `powl_id` + root operator name + top-level child count. POWL generalizes process trees with partial-order sibling dependencies.
- `discover_temporal_profile(log_id)` — discovers per-activity-pair mean + stddev sojourn times. Returns `temporal_profile_id` + pair count. Dict keys are `Tuple[str, str]` — never serialize to JSON directly.

**Abstractions (3 tools)** — the three Phase 3 deferred abstractions, now unlocked because PM4Py 2.7.22.2 provides all required `discover_*` functions natively (including `discover_temporal_profile`, which the 0.3.0 plan incorrectly assumed was missing).
- `abstract_declare(declare_id)` — wraps `declare_to_descr.apply`. No MAX_LEN knob; always returns the full constraint narrative.
- `abstract_log_skeleton(log_skeleton_id)` — wraps `logske_to_descr.apply`. No MAX_LEN knob.
- `abstract_temporal_profile(temporal_profile_id)` — wraps `tempprofile_to_descr.apply`. Handles the tuple-keyed dict internally via pm4py; `truncated` always `False`.

**Visualization (1 tool)**
- `visualize_powl(powl_id)` — Graphviz-backed dual-channel PNG + SVG via `pm4py.save_vis_powl`. Reuses the existing `save_dual_channel` helper; no new infrastructure. Caption includes root operator and child count.

**Conversions (1 tool)**
- `convert_model(source_id, target_kind)` — one tool wraps pm4py's three `convert_to_*` functions. Supported pairs:
  - → `petri_net`: from `bpmn`, `process_tree`, `powl`
  - → `bpmn`: from `petri_net`, `process_tree`
  - → `process_tree`: from `petri_net`, `bpmn`, `powl`
  - Unsupported pairs (e.g. POWL → BPMN — pm4py doesn't expose it directly) raise `InvalidKind` with a clear remediation message. The new handle stamps a `source_handle` breadcrumb on the registry entry so conversion lineage is debuggable.

### Infrastructure

- **4 new registry kinds**: `declare`, `log_skeleton`, `powl`, `temporal_profile` with prefixes `decl-`, `lsk-`, `powl-`, `tprof-` respectively.
- **`source_handle` breadcrumb** on `LogRegistry._Entry` — optional string field that records the handle an artifact was derived from. Stamped by `convert_model`, all 4 new `discover_*` tools, and available via new `registry.source_handle(handle)` accessor. Existing entries default to `None`; fully backward-compatible.
- New `src/pm4py_mcp/tools/conversions.py` module; wired into `pm4py_mcp.tools.__init__` via the existing side-effect-import pattern.
- `scripts/smoke_test_wheel.py` `EXPECTED_CORE_TOOLS` extended with the 9 new tools.

### Design notes

- **POWL abstraction deferred.** `pm4py.algo.querying.llm.abstractions` does NOT ship a `powl_to_descr`. Hand-writing a POWL serializer (StrictPartialOrder + OperatorPOWL + SilentTransition + Transition traversal) is a research-grade endeavor, not a patch. 0.4.0 ships `visualize_powl` only; revisit when/if pm4py upstreams a POWL description function.
- **Model-conversion consolidation.** Three pm4py functions (`convert_to_petri_net`, `convert_to_bpmn`, `convert_to_process_tree`) become one MCP tool with explicit dispatch, since the shape of the operation is genuinely a one-to-one dispatch table and there's no per-source parameterization to hide.

### Deferred to 0.4.1

Everything that requires new infrastructure beyond the existing Graphviz path:

- **Organizational mining** — 5 tools: `discover_handover_network`, `discover_working_together_network`, `discover_subcontracting_network`, `discover_activity_based_resource_similarity`, `discover_organizational_roles`. Separate 1:1 tools matching the OCEL-filter-style precedent, not consolidated.
- **Simulation** — `simulate_log(model_id, num_traces)` via `pm4py.play_out`, returning a fresh `log_id` composable with every Phase 1 tool.
- **Advanced visualization** — `visualize_dotted_chart`, `visualize_performance_spectrum`. Both are matplotlib-backed; requires a new `save_matplotlib_png` helper parallel to `save_dual_channel`.
- **SNA visualization** — `visualize_sna` deferred indefinitely until a matplotlib-backed renderer replaces pm4py's HTML-only pyvis output (useless for Claude clients).
- **`/organizational_analysis` prompt** — pairs naturally with 0.4.1's org-mining tools.

## [0.3.2] - TBD

Dogfooding-driven polish, driven by a same-day full-chain session (`/new_log_onboarding` → `/bottleneck_analysis` → `abstract_case` drill-down) on the Sepsis benchmark. Three concrete problems surfaced and 0.3.2 fixes them. No tool-surface removals; one new tool (`sample_case_ids`) brings the count from 48 to 49.

### Added

- **`sample_case_ids(log_id, n=5, strategy="first"|"longest"|"shortest")`** — return a small sample of case IDs without exporting the log to disk first. Fixes the "how do I get a `case_id` to pass to `abstract_case`?" workflow gap the dogfooding hit. `"longest"`/`"shortest"` sort by event count and include an `event_counts` dict in the response; `"first"` preserves original order.
- **`abstract_case(..., drop_nan_attrs=True)`** — new parameter, default True. Strips `= nan ;` attribute dumps from `case_to_descr` output before returning. Real impact: a 15-event Sepsis case dropped from 11,460 chars (3,041 approx-tokens) to 2,538 chars — **77 % reduction**, no signal lost. Pass `drop_nan_attrs=False` for the exact pre-0.3.2 verbose output.
- **`PM4PY_MCP_CWD_HINT` fallback for output paths** — `export_log` and `render_report` now honor the hint when a relative output path's parent directory doesn't exist under CWD. Closes 0.3.1's "Known" carry-over. New helper `resolve_output_path` in `src/pm4py_mcp/_paths.py` delegated from both tools.

### Changed

- **`/new_log_onboarding` prompt body** gained two guidance additions:
  - A caveat that `get_case_durations` measures case *lifetime*, not hospital/bed time — for readmission-style logs (where one case ID spans admission + later re-presentation), a long p90 may reflect outpatient gaps rather than throughput bottlenecks. Sepsis dogfooding surfaced this: the apparent "93-day p90 hospital stay" was really a 93-day case lifetime with ~4-month readmission intervals.
  - A drill-in hint pointing at `sample_case_ids(..., strategy="longest")` → `abstract_case`.
- `abstract_case` error message now refers callers to `sample_case_ids` (instead of just `get_variants` / `filter`) when the supplied `case_id` isn't in the log.

### Fixed

- Output-path resolution in `export_log` / `render_report` now uses the shared `resolve_output_path` helper. Previously, a relative path with a subdirectory component that didn't exist under CWD would silently create the subdir in a surprising location; now, if `PM4PY_MCP_CWD_HINT` points at a directory where the subdir already exists, that location is used — matching the 0.3.1 input-path resolution semantics.

### Dogfooding receipts

The decision to ship `sample_case_ids` + `drop_nan_attrs` came from an end-to-end session where:
1. `/bottleneck_analysis` on the Sepsis long-stay cohort (207 cases ≥ 30 days) revealed the "long stay" anomaly was actually a 119-day-average `Release A → Return ER` readmission interval (184 cases).
2. Drilling into a specific case required exporting the filtered log to CSV and grepping for case IDs — 0.3.2's `sample_case_ids` closes that loop so Claude can pick a case autonomously.
3. The per-case `abstract_case` output was 90 % NaN padding (27 of ~30 attributes NaN on most events). `drop_nan_attrs=True` cut that to signal-only output.

## [0.3.1] - TBD

Patch release driven by same-day dogfooding of `pm4py-mcp 0.3.0` on the Sepsis benchmark. 0.3.0's prompt templates got the user 80 % of the way but three UX failures surfaced on the first real run. 0.3.1 closes them. No tool surface changes; no breaking changes.

### Added

- **`PM4PY_MCP_CWD_HINT` environment variable.** When `load_event_log` / `load_ocel` receives a relative path that doesn't resolve against the server's CWD, the resolver now falls back to joining the path against `$PM4PY_MCP_CWD_HINT` if it's set. Users configure it once in their MCP server block (`env: { "PM4PY_MCP_CWD_HINT": "${workspaceFolder}" }`) and relative paths just work. Absolute paths are never overridden.
- **Descriptive `FileNotFoundError` messages.** When path resolution still fails, the error now names the input path, the server's CWD, whether `PM4PY_MCP_CWD_HINT` was set, and how to retry — so Claude can act on the error instead of stalling.
- **`get_case_durations` in the `/new_log_onboarding` chain.** Median / p90 / p95 / p99 duration percentiles are the cheapest, highest-signal anomaly indicator on a real log. 0.3.0's onboarding narrative missed the Sepsis long tail (median 5.3 days, p90 = 93 days); 0.3.1's doesn't.
- **`get_variants(log_id, top_k=10)` as the narrative variant step in `/new_log_onboarding`.** `abstract_variants` (which returned ~10 KB of fat-middle prose on Sepsis while the top 5 variants covered <10 % of cases) is demoted to an **optional drill-in** step with a tight `max_len=3000` — invoked only when step 4 surfaces a long variant worth explaining.
- **Shared "Path tip" footer across all 6 prompt templates.** Every `@mcp.prompt` body now ends with remediation guidance so Claude knows how to recover when relative paths fail — without requiring the server to be restarted. Implementation: one helper in `src/pm4py_mcp/prompts/_shared.py::path_tip_footer`; one-line concatenation per prompt.

### Fixed

- **POSIX `OSError(ENAMETOOLONG)` in `set_domain_context` with long SOP payloads.** On Linux/macOS, `Path.is_file()` calls `os.stat()` which raises `OSError(ENAMETOOLONG)` when the "path" string exceeds `NAME_MAX` (255 bytes). 0.3.0's `_resolve_text_or_path` caught errors around `Path()` construction but not around `is_file()`, so passing a 10-20 KB inline text context crashed the tool on POSIX while working on Windows. CI was red on every Linux + macOS cell between the Slice 1 commit and now; local tests passed because the developer was on Windows. Fix: wrap `is_file()` in the same try/except block. (commit `c33117f`, already on `main` but not on any PyPI release before 0.3.1.)

### Infrastructure

- New shared helper `src/pm4py_mcp/_paths.py::resolve_input_path` (parallel to `_time.py` / `_tokens.py`). Single source of truth for user-supplied input paths; reused by `load_event_log` and `load_ocel`.
- `scripts/smoke_test_wheel.py` now reads the expected version string from `importlib.metadata.version("pm4py-mcp")` instead of hardcoding it. Future releases won't need a smoke-test edit.
- New test module `tests/test_paths.py` (7 cases covering absolute/relative/hint/tilde combinations). Extended `tests/test_tools_io.py` + `tests/test_tools_ocel_io.py` to assert the new error message shape. Extended `tests/test_prompts_mcp.py` with a parametrized test that every prompt body includes the `PM4PY_MCP_CWD_HINT` footer.

### Known limitations

- **`render_report` and `export_log` honor their `path` arg verbatim** when it has a directory component (same 0.2.0 / 0.3.0 behavior). The `PM4PY_MCP_CWD_HINT` fallback applies to *input* paths (`load_event_log`, `load_ocel`) only in 0.3.1. Output-path consistency is planned for 0.3.2 using the same helper.
- **`abstract_variants` fat-middle problem is not fully solved.** 0.3.1 sidesteps it by not calling `abstract_variants` as the primary variant tool in `/new_log_onboarding`; the function itself still returns up to `max_len` chars of all ranked variants. A server-side "top-N-only" mode is deferred to 0.4.0 (requires changes to how pm4py's underlying `log_to_variants_descr` is invoked).

## [0.3.0] - TBD

Phase 3 — **agentic layer.** 12 new tools + 6 prompts bring the total surface to **48 tools** plus a curated prompt library. The focus of this release is *LLM reasoning over PM artifacts*: previously Claude could render a Petri net (a PNG) but couldn't reason about its structure; now every major artifact has a textual abstraction the LLM reads directly.

### Added

**Textual abstractions (9 tools)** — wrap `pm4py.algo.querying.llm.abstractions.*_to_descr`. Every abstraction returns a uniform `{content, approx_tokens, truncated, source_handle, tool}` dict so the LLM can decide when to re-request with a tighter `max_len`.
- `abstract_log_features(log_id, max_len=10_000)` — log-level feature description (concurrency, skeleton, timing signal).
- `abstract_log_attributes(log_id, max_len=10_000)` — case/event attribute distributions in text.
- `abstract_variants(log_id, max_len=10_000, include_performance=True)` — ranked variants with durations (pm4py internally computes; no top_k param — truncation-driven).
- `abstract_dfg(log_id, max_len=10_000, include_performance=True)` — directly-follows graph as prose with sojourn times. Takes `log_id` (not `dfg_id`) — pm4py recomputes the DFG internally.
- `abstract_case(log_id, case_id, include_event_attributes=True)` — single-case walk-through. Raises `UnsupportedFormat` for unknown case IDs. No `max_len` knob (pm4py's `case_to_descr` doesn't expose one).
- `abstract_stream(log_id, max_len=10_000)` — tail of events in reverse-chronological order. Useful for "what happened most recently?" questions.
- `abstract_petri_net(petri_id)` — structural description of places/transitions/markings. No `max_len` knob; `truncated` is always `False`.
- `abstract_ocel(ocel_id, object_type, max_len=10_000)` — per-object-type event description. Validates `object_type` against the OCEL.
- `abstract_ocdfg(ocel_id, max_len=10_000, include_performance=True)` — object-centric DFG in prose. Takes `ocel_id` directly (pm4py recomputes).

**Domain context (2 tools)**
- `set_domain_context(text_or_path, name="default")` — register an SOP / glossary / process description under a name. Accepts inline text OR a file path (auto-detected). Capped at 20 KB per context and 16 named contexts total. Contexts survive across tool calls in the same server process.
- `get_domain_context(name="default")` — retrieve stored context for inspection. Raises `ContextNotFound` if unknown.

Registered contexts are automatically prepended to every prompt template's body, so `@mcp.prompt` expansions respect user-supplied domain knowledge without the user having to re-paste it each time.

**Reports (1 tool)**
- `render_report(title, findings, artifact_paths=None, output_path=None)` — assemble a Markdown report with ISO-8601 timestamp, the LLM-authored findings, an Artifacts section (images embedded inline, other files as links), and a pm4py-mcp version footer. Bare filenames land in the workspace; absolute paths are honored as-is.

**Prompt library (6 prompts via `@mcp.prompt`)** — user-invoked slash commands that seed canonical PM investigations.
- `new_log_onboarding(log_path)` — 2-minute first-impression summary.
- `conformance_workflow(log_path, noise_threshold=0.2)` — load + discover + token replay + alignments + compare.
- `bottleneck_analysis(log_path)` — find slowest variants and bottleneck DFG edges.
- `variant_exploration(log_path, k=5)` — top-k variants + drill into the dominant one.
- `ocel_flattening_workflow(ocel_path)` — compare object-type perspectives of an OCEL.
- `executive_summary(log_id_or_path, title)` — consolidate findings via `render_report`.

**Infrastructure**
- `src/pm4py_mcp/_tokens.py` — char÷4 token-count heuristic in its own module. Easy swap-in for a real tokenizer later.
- `AbstractionResult` dataclass in `models.py` with `.build()` classmethod that computes `approx_tokens` + `truncated` from content length.
- `scripts/download_benchmark_logs.py` — pulls Sepsis (198 KB), BPI 2012, BPI 2017 from 4TU.ResearchData with MD5 verification. Logs land in `examples/benchmarks/` (gitignored).
- End-to-end Phase 3 stdio workflow test in [tests/test_workflow_phase3_stdio.py](tests/test_workflow_phase3_stdio.py): load → abstract_variants → abstract_dfg → discover_petri_net → abstract_petri_net → set/get domain context → render_report with embedded narrative.

### Design note — abstract-then-prompt paradigm

Phase 1 and Phase 2 grew the *verb* surface. Phase 3 grows the *reasoning* surface. A user asking "where's the bottleneck?" in 0.2.0 got a PNG Claude couldn't read; in 0.3.0 the same prompt triggers `/bottleneck_analysis`, which runs `abstract_dfg(include_performance=True)` + `abstract_variants(include_performance=True)` and hands Claude the numbers directly. This is Berti's framework: *abstract the artifact into text, then prompt the LLM on the text.*

### Deferred (explicit)

- `run_duckdb_sql(log_id, sql)` — requires adding the `duckdb` dep. Slotted for 0.3.1.
- `semantic_anomaly_detect(log_id)` — needs `ctx.session.create_message`, which is only available in `ServerTaskContext` (via `@server.task()`), not regular `@server.tool()`. Meaningful re-architecture; target 0.3.1 or 0.4.0.
- `abstract_declare`, `abstract_log_skeleton`, `abstract_temporal_profile` — will land with Phase 2 Part 2 (0.4.0) when their corresponding discovery tools exist.

### Requires

- Same runtime deps as 0.2.0. No new packages — the abstractions use `pm4py.algo.querying.llm.abstractions.*` modules already shipped with pm4py 2.7+.
- No Graphviz change from 0.2.0.

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

[Unreleased]: https://github.com/azizketata/pm4py-mcp/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.4.1
[0.4.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.4.0
[0.3.2]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.3.2
[0.3.1]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.3.1
[0.3.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.3.0
[0.2.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.2.0
[0.1.0]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.1.0
[0.0.1]: https://github.com/azizketata/pm4py-mcp/releases/tag/v0.0.1
