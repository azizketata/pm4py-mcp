"""Phase 1 — statistics tools.

Every stats tool takes a ``log_id`` handle from the registry and returns a
compact dict. Long output (full variant lists, full per-case duration arrays)
is avoided — we summarize rather than dump.
"""

from __future__ import annotations

import statistics
from typing import Any, Literal, cast

import pandas as pd
import pm4py

from pm4py_mcp.server import mcp, registry

# How many top variants to list in the response.
_VARIANTS_CAP = 20
# Reported percentiles for case duration summaries.
_PERCENTILES = (50, 75, 90, 95, 99)


@mcp.tool()
def get_variants(log_id: str, top_k: int = _VARIANTS_CAP) -> dict[str, Any]:
    """Return the most-common trace variants and their counts.

    Caps output at ``top_k`` variants (default 20) and includes the total
    variant count so the caller knows if the list was truncated.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)

    variants_dict = pm4py.get_variants(log)
    items = sorted(variants_dict.items(), key=lambda kv: -kv[1])
    top = items[:top_k]
    return {
        "log_id": log_id,
        "total_variants": len(variants_dict),
        "returned": len(top),
        "variants": [{"trace": list(trace), "count": int(count)} for trace, count in top],
    }


@mcp.tool()
def get_start_end_activities(log_id: str) -> dict[str, Any]:
    """Return the frequency of start and end activities across all cases.

    Two dicts keyed by activity name → count. Useful for spotting
    unexpected entry / exit points in a process.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    start = pm4py.get_start_activities(log)
    end = pm4py.get_end_activities(log)
    return {
        "log_id": log_id,
        "start": {str(k): int(v) for k, v in start.items()},
        "end": {str(k): int(v) for k, v in end.items()},
    }


def _percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolation percentile on a pre-sorted list."""
    if not sorted_values:
        raise ValueError("Cannot compute percentiles on an empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (p / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


@mcp.tool()
def get_case_durations(log_id: str) -> dict[str, Any]:
    """Return summary statistics for per-case durations (seconds).

    Returns ``count``, ``min``, ``max``, ``mean``, ``median``, and the
    50/75/90/95/99 percentiles. The full per-case list is NOT returned —
    it can be 100k+ floats on a real log and blow the response cap.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    durations_raw = pm4py.get_all_case_durations(log)
    durations = sorted(float(d) for d in durations_raw)

    if not durations:
        return {"log_id": log_id, "count": 0}

    return {
        "log_id": log_id,
        "count": len(durations),
        "min": durations[0],
        "max": durations[-1],
        "mean": statistics.fmean(durations),
        "median": statistics.median(durations),
        "percentiles": {f"p{p}": _percentile(durations, p) for p in _PERCENTILES},
    }


@mcp.tool()
def sample_case_ids(
    log_id: str,
    n: int = 5,
    strategy: Literal["first", "longest", "shortest"] = "first",
) -> dict[str, Any]:
    """Return a small sample of case IDs from a log.

    Useful for picking a concrete ``case_id`` to pass to ``abstract_case``
    without having to export the log to disk first.

    Strategies:
    - ``"first"``: IDs in original order (cheap; no sort).
    - ``"longest"``: the ``n`` cases with the most events.
    - ``"shortest"``: the ``n`` cases with the fewest events.

    For ``longest`` / ``shortest``, the response includes an ``event_counts``
    dict so callers can see the sort key; ``first`` omits it.
    """
    if n < 1:
        return {"log_id": log_id, "case_ids": [], "total_cases": 0, "strategy": strategy}

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    case_sizes = log.groupby("case:concept:name").size()
    total = int(case_sizes.shape[0])

    if strategy == "first":
        seen: list[str] = []
        for cid in log["case:concept:name"]:
            if cid not in seen:
                seen.append(str(cid))
                if len(seen) >= n:
                    break
        return {
            "log_id": log_id,
            "case_ids": seen,
            "total_cases": total,
            "strategy": "first",
        }

    # strategy is "longest" or "shortest" at this point; first was handled above.
    selected = case_sizes.nlargest(n) if strategy == "longest" else case_sizes.nsmallest(n)

    return {
        "log_id": log_id,
        "case_ids": [str(k) for k in selected.index.tolist()],
        "total_cases": total,
        "strategy": strategy,
        "event_counts": {str(k): int(v) for k, v in selected.items()},
    }


@mcp.tool()
def get_cycle_time(log_id: str) -> dict[str, Any]:
    """Return the average cycle time (seconds between case completions).

    Unlike ``get_case_durations`` (which measures elapsed time per case),
    cycle time measures throughput — inter-completion delay at the process
    level. Useful for capacity planning.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    ct = float(pm4py.get_cycle_time(log))
    return {"log_id": log_id, "cycle_time_seconds": ct}


__all__ = [
    "get_case_durations",
    "get_cycle_time",
    "get_start_end_activities",
    "get_variants",
    "sample_case_ids",
]
