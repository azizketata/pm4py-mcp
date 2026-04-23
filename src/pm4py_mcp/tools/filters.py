"""Phase 1 — filter tools.

Filters are pure — each call mints a fresh ``log_id`` so the user can chain
filters and retain references to intermediate states. The response shape is
a :class:`FilterResult` with before/after counts so the LLM can reason about
how aggressive each filter was.

All filters raise :class:`HandleNotFound` / :class:`InvalidKind` via the
registry if the input handle is stale or of the wrong kind.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import pandas as pd
import pm4py

from pm4py_mcp._time import normalize_datetime as _normalize_datetime
from pm4py_mcp.models import FilterResult
from pm4py_mcp.server import mcp, registry


def _counts(log: pd.DataFrame) -> tuple[int, int]:
    """Return (num_cases, num_events) for a pm4py-formatted DataFrame."""
    return int(log["case:concept:name"].nunique()), len(log)


def _wrap(
    *,
    source_log_id: str,
    filtered: pd.DataFrame,
    before: tuple[int, int],
    filter_name: str,
) -> dict[str, Any]:
    after = _counts(filtered)
    new_id = registry.put("log", filtered)
    return FilterResult(
        new_log_id=new_id,
        source_log_id=source_log_id,
        filter=filter_name,
        num_cases_before=before[0],
        num_cases_after=after[0],
        num_events_before=before[1],
        num_events_after=after[1],
    ).as_dict()


@mcp.tool()
def filter_variants(
    log_id: str,
    top_k: int | None = None,
    variants: list[list[str]] | None = None,
    retain: bool = True,
) -> dict[str, Any]:
    """Filter a log by trace variant.

    Exactly one of ``top_k`` and ``variants`` must be given:

    - ``top_k=N`` — keep (or remove, if ``retain=False``) the N most frequent
      variants. Useful for ignoring rare noise.
    - ``variants=[[act1, act2, ...], ...]`` — keep/remove specific variants
      by their full activity sequence.
    """
    if (top_k is None) == (variants is None):
        raise ValueError("Pass exactly one of top_k= or variants=.")

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    before = _counts(log)

    if top_k is not None:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        all_variants = pm4py.get_variants(log)
        sorted_variants = sorted(all_variants.items(), key=lambda kv: -kv[1])
        chosen = [variant for variant, _count in sorted_variants[:top_k]]
    else:
        assert variants is not None
        chosen = [tuple(v) for v in variants]

    filtered = pm4py.filter_variants(log, chosen, retain=retain)
    return _wrap(
        source_log_id=log_id,
        filtered=filtered,
        before=before,
        filter_name="filter_variants",
    )


@mcp.tool()
def filter_time_range(
    log_id: str,
    start: str,
    end: str,
    mode: Literal[
        "events",
        "traces_contained",
        "traces_intersecting",
        "traces_starting_in",
        "traces_starting_in_exclude",
        "traces_completing_in",
        "traces_completing_in_exclude",
    ] = "events",
) -> dict[str, Any]:
    """Filter a log by a time window.

    ``start`` and ``end`` are ISO-8601 datetime strings. ``mode`` chooses
    which notion of "within the window" applies:

    - ``"events"`` (default) — keep individual events inside the window.
    - ``"traces_contained"`` — keep traces entirely within the window.
    - ``"traces_intersecting"`` — keep traces with any event in the window.
    - ``"traces_starting_in"`` / ``"traces_completing_in"`` — keep traces
      whose first/last event falls in the window.
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    before = _counts(log)

    filtered = pm4py.filter_time_range(
        log, _normalize_datetime(start), _normalize_datetime(end), mode=mode
    )
    return _wrap(
        source_log_id=log_id,
        filtered=filtered,
        before=before,
        filter_name="filter_time_range",
    )


@mcp.tool()
def filter_attribute_values(
    log_id: str,
    attribute: str,
    values: list[str],
    retain: bool = True,
    level: Literal["event", "case"] = "event",
) -> dict[str, Any]:
    """Filter a log by event or case attribute values.

    ``level='event'`` removes individual events; ``level='case'`` removes
    entire cases. ``retain=True`` keeps the matching rows; ``False`` drops
    them. The ``level`` parameter is passed explicitly to avoid PM4Py's
    deprecation warning when it defaults to ``None``.
    """
    if not values:
        raise ValueError("values must be a non-empty list of attribute values")

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    before = _counts(log)

    filtered = pm4py.filter_event_attribute_values(
        log,
        attribute,
        values,
        level=level,
        retain=retain,
    )
    return _wrap(
        source_log_id=log_id,
        filtered=filtered,
        before=before,
        filter_name="filter_attribute_values",
    )


@mcp.tool()
def filter_case_size(
    log_id: str,
    min_size: int,
    max_size: int,
) -> dict[str, Any]:
    """Keep only cases with an event count in ``[min_size, max_size]``.

    Useful for removing outlier cases (very short or very long traces)
    before discovery / conformance.
    """
    if min_size < 0 or max_size < min_size:
        raise ValueError(
            f"Expected 0 <= min_size <= max_size, got min_size={min_size}, max_size={max_size}"
        )

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    before = _counts(log)

    filtered = pm4py.filter_case_size(log, min_size, max_size)
    return _wrap(
        source_log_id=log_id,
        filtered=filtered,
        before=before,
        filter_name="filter_case_size",
    )


@mcp.tool()
def filter_case_performance(
    log_id: str,
    min_seconds: float,
    max_seconds: float,
) -> dict[str, Any]:
    """Keep only cases whose total elapsed time is in ``[min_seconds, max_seconds]``.

    Performance is measured as ``last_event_timestamp - first_event_timestamp``
    of each case, in seconds. Useful for isolating slow or fast cases.
    """
    if min_seconds < 0 or max_seconds < min_seconds:
        raise ValueError(
            f"Expected 0 <= min_seconds <= max_seconds, "
            f"got min_seconds={min_seconds}, max_seconds={max_seconds}"
        )

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)
    before = _counts(log)

    filtered = pm4py.filter_case_performance(log, min_seconds, max_seconds)
    return _wrap(
        source_log_id=log_id,
        filtered=filtered,
        before=before,
        filter_name="filter_case_performance",
    )


__all__ = [
    "filter_attribute_values",
    "filter_case_performance",
    "filter_case_size",
    "filter_time_range",
    "filter_variants",
]
