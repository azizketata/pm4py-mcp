"""Phase 1 — conformance tools.

Compares a traditional log against a Petri-net model. Two algorithms:

- **Token-based replay** — fast, non-iterative, works well on sound nets.
  Returns per-trace fitness + token counts; we aggregate into mean fitness
  and fit-case count.
- **Alignments** — slower but more robust. Returns per-trace alignment
  moves + cost + fitness. Can exceed five minutes on a 500 MB log, so the
  tool is async and emits progress via ``ctx.report_progress`` to keep
  client request timeouts alive.

Only aggregate stats are returned — never the per-trace list, which can be
100k+ rows on a real log.
"""

from __future__ import annotations

import statistics
from typing import Any, cast

import pandas as pd
import pm4py
from mcp.server.fastmcp import Context

from pm4py_mcp.models import ConformanceResult
from pm4py_mcp.server import mcp, registry

_Ctx = Context[Any, Any, Any]


def _num_cases(log: pd.DataFrame) -> int:
    return int(log["case:concept:name"].nunique())


def _extract_trace_fitness(diag: dict[str, Any], key: str) -> float:
    """Return the fitness of a single trace, defaulting to 0.0 if missing."""
    value = diag.get(key)
    if value is None:
        return 0.0
    return float(value)


@mcp.tool()
def conformance_token_replay(log_id: str, petri_id: str) -> dict[str, Any]:
    """Token-based replay conformance check.

    Returns mean trace fitness (0.0..1.0) and the count of perfectly-fit
    traces. For detailed per-trace diagnostics, re-run the PM4Py
    ``conformance_diagnostics_token_based_replay`` directly — we keep the
    MCP response compact on purpose.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    _, model = registry.get(petri_id, expected_kind="petri_net")
    log = cast(pd.DataFrame, log_obj)
    net, im, fm = model

    per_trace = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)
    fitnesses = [_extract_trace_fitness(d, "trace_fitness") for d in per_trace]
    num_fit = sum(1 for d in per_trace if d.get("trace_is_fit", False))

    return ConformanceResult(
        log_id=log_id,
        petri_id=petri_id,
        algorithm="token_replay",
        num_cases=_num_cases(log),
        num_fit_cases=num_fit,
        mean_trace_fitness=statistics.fmean(fitnesses) if fitnesses else 0.0,
    ).as_dict()


@mcp.tool()
async def conformance_alignments(
    log_id: str,
    petri_id: str,
    multi_processing: bool = False,
    ctx: _Ctx | None = None,
) -> dict[str, Any]:
    """Alignment-based conformance check.

    More accurate than token replay but slower — can take minutes on large
    logs. ``multi_processing=True`` parallelizes across cores (disabled by
    default since Windows multiprocessing has spawn-restrictions that can
    interact badly with the stdio transport).

    Emits progress events so the client keeps the request alive past its
    default timeout.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    _, model = registry.get(petri_id, expected_kind="petri_net")
    log = cast(pd.DataFrame, log_obj)
    net, im, fm = model
    num_cases = _num_cases(log)

    if ctx is not None:
        await ctx.report_progress(
            progress=0.0,
            total=float(num_cases),
            message=f"Computing alignments for {num_cases} cases",
        )

    per_trace = pm4py.conformance_diagnostics_alignments(
        log, net, im, fm, multi_processing=multi_processing
    )

    if ctx is not None:
        await ctx.report_progress(
            progress=float(num_cases),
            total=float(num_cases),
            message="Aggregating fitness",
        )

    fitnesses = [_extract_trace_fitness(d, "fitness") for d in per_trace]
    # Alignments report fractional fitness; "fit" = fitness == 1.0
    num_fit = sum(1 for f in fitnesses if f >= 0.999999)

    return ConformanceResult(
        log_id=log_id,
        petri_id=petri_id,
        algorithm="alignments",
        num_cases=num_cases,
        num_fit_cases=num_fit,
        mean_trace_fitness=statistics.fmean(fitnesses) if fitnesses else 0.0,
    ).as_dict()


__all__ = [
    "conformance_alignments",
    "conformance_token_replay",
]
