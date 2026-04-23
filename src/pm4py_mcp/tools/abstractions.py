"""Phase 3 Slice 1 — log-level textual abstractions.

Wrap ``pm4py.algo.querying.llm.abstractions.*_to_descr.apply`` to emit
token-budget-aware natural-language descriptions of event logs that Claude
can **reason over** — instead of just rendering a PNG it can't interpret.

Every tool returns :class:`AbstractionResult` shape::

    {"content": str, "approx_tokens": int, "truncated": bool,
     "source_handle": str, "tool": str}

pm4py's underlying functions return plain ``str``; we wrap with our own
metadata because (a) pm4py's truncation is character-based at ``MAX_LEN``
and the LLM needs to know it was truncated, (b) planning around context
budget requires a token estimate.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
import pm4py
from pm4py.algo.querying.llm.abstractions import (
    case_to_descr,
    log_to_cols_descr,
    log_to_dfg_descr,
    log_to_fea_descr,
    log_to_variants_descr,
    net_to_descr,
    ocel_fea_descr,
    ocel_ocdfg_descr,
    stream_to_descr,
)
from pm4py.objects.ocel.obj import OCEL

from pm4py_mcp.errors import UnsupportedFormat
from pm4py_mcp.models import AbstractionResult
from pm4py_mcp.server import mcp, registry

_DEFAULT_MAX_LEN = 10_000


def _get_log(log_id: str) -> pd.DataFrame:
    _, log_obj = registry.get(log_id, expected_kind="log")
    return cast(pd.DataFrame, log_obj)


@mcp.tool()
def abstract_log_features(
    log_id: str,
    max_len: int = _DEFAULT_MAX_LEN,
) -> dict[str, Any]:
    """Textual description of log-level features (activity set, concurrency, timing).

    Wraps ``pm4py.algo.querying.llm.abstractions.log_to_fea_descr.apply``.
    Truncated at ``max_len`` characters (pm4py's native limit).
    """
    log = _get_log(log_id)
    content = log_to_fea_descr.apply(
        log,
        parameters={log_to_fea_descr.Parameters.MAX_LEN: max_len},
    )
    return AbstractionResult.build(content, max_len, log_id, "abstract_log_features").as_dict()


@mcp.tool()
def abstract_log_attributes(
    log_id: str,
    max_len: int = _DEFAULT_MAX_LEN,
) -> dict[str, Any]:
    """Textual description of attribute distributions (value frequencies, quantiles).

    Wraps ``log_to_cols_descr.apply``. Useful for the LLM to understand what
    slicing dimensions exist in the log.
    """
    log = _get_log(log_id)
    content = log_to_cols_descr.apply(
        log,
        parameters={log_to_cols_descr.Parameters.MAX_LEN: max_len},
    )
    return AbstractionResult.build(content, max_len, log_id, "abstract_log_attributes").as_dict()


@mcp.tool()
def abstract_variants(
    log_id: str,
    max_len: int = _DEFAULT_MAX_LEN,
    include_performance: bool = True,
) -> dict[str, Any]:
    """Trace variants + frequencies + (optionally) per-variant performance.

    Wraps ``log_to_variants_descr.apply``. Variants are auto-ranked by
    frequency internally; truncation happens when the combined description
    hits ``max_len`` characters — not via a ``top_k`` parameter.
    """
    log = _get_log(log_id)
    content = log_to_variants_descr.apply(
        log,
        parameters={
            log_to_variants_descr.Parameters.MAX_LEN: max_len,
            log_to_variants_descr.Parameters.INCLUDE_PERFORMANCE: include_performance,
        },
    )
    return AbstractionResult.build(content, max_len, log_id, "abstract_variants").as_dict()


@mcp.tool()
def abstract_dfg(
    log_id: str,
    max_len: int = _DEFAULT_MAX_LEN,
    include_performance: bool = True,
) -> dict[str, Any]:
    """Directly-follows graph rendered as text.

    Note: takes ``log_id``, **not** ``dfg_id``. pm4py computes the DFG
    internally for description. For the rendered PNG/SVG, use Phase 1's
    ``discover_dfg`` → ``visualize_dfg`` pair instead.
    """
    log = _get_log(log_id)
    content = log_to_dfg_descr.apply(
        log,
        parameters={
            log_to_dfg_descr.Parameters.MAX_LEN: max_len,
            log_to_dfg_descr.Parameters.INCLUDE_PERFORMANCE: include_performance,
        },
    )
    return AbstractionResult.build(content, max_len, log_id, "abstract_dfg").as_dict()


@mcp.tool()
def abstract_case(
    log_id: str,
    case_id: str,
    include_event_attributes: bool = True,
) -> dict[str, Any]:
    """Describe one case as a natural-language walkthrough of its events.

    ``case_id`` must match a value in the log's ``case:concept:name`` column.
    pm4py's ``case_to_descr`` has no ``MAX_LEN`` parameter — the full case
    description is always returned, so ``truncated`` is always ``False``.
    """
    log = _get_log(log_id)
    case_df = log[log["case:concept:name"] == case_id]
    if case_df.empty:
        raise UnsupportedFormat(
            f"Case {case_id!r} not found in log {log_id}. "
            "Use get_variants or filter tools to inspect available case ids."
        )
    # case_to_descr needs a legacy Trace (not a DataFrame slice). Convert.
    event_log = pm4py.convert_to_event_log(case_df)
    if len(event_log) == 0:
        raise UnsupportedFormat(f"Could not convert case {case_id!r} to a Trace object.")
    trace = event_log[0]
    content = case_to_descr.apply(
        trace,
        parameters={
            case_to_descr.Parameters.INCLUDE_EVENT_ATTRIBUTES: include_event_attributes,
        },
    )
    return AbstractionResult.build(content, None, log_id, "abstract_case").as_dict()


@mcp.tool()
def abstract_stream(
    log_id: str,
    max_len: int = _DEFAULT_MAX_LEN,
) -> dict[str, Any]:
    """Tail of events in reverse-chronological order.

    Answers "what happened recently in this log?" without computing variants
    or discovering a model. Wraps ``stream_to_descr.apply``.
    """
    log = _get_log(log_id)
    content = stream_to_descr.apply(
        log,
        parameters={stream_to_descr.Parameters.MAX_LEN: max_len},
    )
    return AbstractionResult.build(content, max_len, log_id, "abstract_stream").as_dict()


@mcp.tool()
def abstract_petri_net(petri_id: str) -> dict[str, Any]:
    """Describe a Petri net (from ``discover_petri_net``) in natural language.

    Wraps ``net_to_descr.apply(net, im, fm)``. Enumerates places, transitions,
    arcs, and the initial / final markings. pm4py's ``net_to_descr`` has no
    ``MAX_LEN`` parameter — the full description is always returned, so
    ``truncated`` is always ``False``.
    """
    _, payload = registry.get(petri_id, expected_kind="petri_net")
    net, im, fm = payload
    content = net_to_descr.apply(net, im, fm)
    return AbstractionResult.build(content, None, petri_id, "abstract_petri_net").as_dict()


@mcp.tool()
def abstract_ocel(
    ocel_id: str,
    object_type: str,
    max_len: int = _DEFAULT_MAX_LEN,
) -> dict[str, Any]:
    """Textual description of OCEL features for a single object type.

    ``object_type`` must be one of the OCEL's object types (see ``describe_ocel``).
    Wraps ``ocel_fea_descr.apply(ocel, object_type)``. Useful before deciding
    which object type to ``flatten_ocel`` on.
    """
    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)

    valid_types = list(ocel.objects["ocel:type"].unique()) if len(ocel.objects) else []
    if object_type not in valid_types:
        raise UnsupportedFormat(
            f"Object type {object_type!r} not in OCEL {ocel_id}. "
            f"Available object types: {sorted(valid_types)}"
        )

    content = ocel_fea_descr.apply(
        ocel,
        object_type,
        parameters={ocel_fea_descr.Parameters.MAX_LEN: max_len},
    )
    return AbstractionResult.build(content, max_len, ocel_id, "abstract_ocel").as_dict()


@mcp.tool()
def abstract_ocdfg(
    ocel_id: str,
    max_len: int = _DEFAULT_MAX_LEN,
    include_performance: bool = True,
) -> dict[str, Any]:
    """Object-centric directly-follows graph as text.

    Note: takes ``ocel_id``, **not** ``ocdfg_id``. pm4py computes the OCDFG
    internally for description. For the rendered version, use Phase 2's
    ``discover_ocdfg`` → ``visualize_ocdfg`` pair.
    """
    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)

    content = ocel_ocdfg_descr.apply(
        ocel,
        parameters={
            ocel_ocdfg_descr.Parameters.MAX_LEN: max_len,
            ocel_ocdfg_descr.Parameters.INCLUDE_PERFORMANCE: include_performance,
        },
    )
    return AbstractionResult.build(content, max_len, ocel_id, "abstract_ocdfg").as_dict()


__all__ = [
    "abstract_case",
    "abstract_dfg",
    "abstract_log_attributes",
    "abstract_log_features",
    "abstract_ocdfg",
    "abstract_ocel",
    "abstract_petri_net",
    "abstract_stream",
    "abstract_variants",
]
