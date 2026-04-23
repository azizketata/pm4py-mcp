## Summary

<!-- What does this PR do? 1-3 bullets. -->

## Phase / scope

<!-- Which roadmap phase does this belong to? If Phase 0, does it touch any of the locked architectural decisions in CLAUDE.md? -->

- [ ] Phase 0 (foundations)
- [ ] Phase 1 (core traditional-log toolkit)
- [ ] Phase 2+ (OCEL, agentic, platform)
- [ ] Docs / governance / CI only

## DCO

- [ ] All commits are signed off (`git commit -s`). The DCO bot will block merge otherwise.

## Test plan

<!-- Check all that were run locally. Which testing-pyramid layers exercise the change? -->

- [ ] `uv run ruff format --check src tests`
- [ ] `uv run ruff check src tests`
- [ ] `uv run mypy src`
- [ ] `uv run pytest` (layers 1-3)
- [ ] Manual MCP Inspector verification (if tool surface changed)

## Architectural guardrails

- [ ] No tool returns an event log, DataFrame, or raw binary > ~100 KB.
- [ ] No tool accepts both XES logs and OCEL objects (use the parallel namespace).
- [ ] No new `pip install` instructions in README.
- [ ] Long-running tools emit progress via `ctx.report_progress`.
- [ ] Tools raise exceptions on error instead of returning error strings.
