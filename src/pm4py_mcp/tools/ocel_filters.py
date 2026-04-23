"""Phase 2 Slice 3 — OCEL 2.0 filter tools.

Four consolidated verbs rather than the seven separate PM4Py filters — the
``strategy`` / ``level`` dispatch reduces the tool surface the LLM has to
pick from. Every filter is pure: each call mints a fresh ``ocel_id`` so
filter chains retain every intermediate state.

Never returns the OCEL itself — always a handle plus before/after counts.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import pm4py
from pm4py.objects.ocel.obj import OCEL

from pm4py_mcp._time import normalize_datetime
from pm4py_mcp.errors import UnsupportedFormat
from pm4py_mcp.models import OcelFilterResult
from pm4py_mcp.server import mcp, registry

_CC_STRATEGIES = ("activity", "object", "otype", "length")


def _counts(ocel: OCEL) -> tuple[int, int]:
    """Return (num_events, num_objects) for an OCEL."""
    return len(ocel.events), len(ocel.objects)


def _wrap(
    *,
    source_ocel_id: str,
    filtered: OCEL,
    before: tuple[int, int],
    filter_name: str,
) -> dict[str, Any]:
    after = _counts(filtered)
    new_id = registry.put("ocel", filtered)
    return OcelFilterResult(
        new_ocel_id=new_id,
        source_ocel_id=source_ocel_id,
        filter=filter_name,
        num_events_before=before[0],
        num_events_after=after[0],
        num_objects_before=before[1],
        num_objects_after=after[1],
    ).as_dict()


@mcp.tool()
def filter_ocel_time_range(ocel_id: str, start: str, end: str) -> dict[str, Any]:
    """Keep only events whose timestamp falls in ``[start, end]``.

    ``start`` and ``end`` accept ISO-8601 strings (``2024-01-01T08:00:00``).
    pm4py's underlying filter parses with ``'%Y-%m-%d %H:%M:%S'``, so we
    normalize via pandas first.
    """
    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)
    before = _counts(ocel)

    filtered = pm4py.filter_ocel_events_timestamp(
        ocel, normalize_datetime(start), normalize_datetime(end)
    )
    return _wrap(
        source_ocel_id=ocel_id,
        filtered=filtered,
        before=before,
        filter_name="filter_ocel_time_range",
    )


@mcp.tool()
def filter_ocel_attribute(
    ocel_id: str,
    attribute: str,
    values: list[str],
    level: Literal["event", "object"] = "event",
    retain: bool = True,
) -> dict[str, Any]:
    """Filter an OCEL by event or object attribute values.

    ``level='event'`` dispatches to ``pm4py.filter_ocel_event_attribute``;
    ``level='object'`` dispatches to ``pm4py.filter_ocel_object_attribute``.
    ``retain=True`` keeps the matching rows, ``False`` drops them — this
    maps to PM4Py's ``positive`` parameter.
    """
    if not values:
        raise ValueError("values must be a non-empty list of attribute values")

    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)
    before = _counts(ocel)

    if level == "event":
        filtered = pm4py.filter_ocel_event_attribute(ocel, attribute, values, positive=retain)
    elif level == "object":
        filtered = pm4py.filter_ocel_object_attribute(ocel, attribute, values, positive=retain)
    else:
        raise UnsupportedFormat(f"Unknown level {level!r}. Expected 'event' or 'object'.")

    return _wrap(
        source_ocel_id=ocel_id,
        filtered=filtered,
        before=before,
        filter_name=f"filter_ocel_attribute({level})",
    )


@mcp.tool()
def filter_ocel_object_types(
    ocel_id: str,
    types: list[str],
    retain: bool = True,
) -> dict[str, Any]:
    """Keep or drop entire object types (and every event that only touched them).

    ``types=['order', 'delivery']`` with ``retain=True`` keeps only events/objects
    related to orders and deliveries; with ``retain=False`` drops them.
    """
    if not types:
        raise ValueError("types must be a non-empty list of object-type names")

    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)
    before = _counts(ocel)

    filtered = pm4py.filter_ocel_object_types(ocel, types, positive=retain)
    return _wrap(
        source_ocel_id=ocel_id,
        filtered=filtered,
        before=before,
        filter_name="filter_ocel_object_types",
    )


@mcp.tool()
def filter_ocel_cc(
    ocel_id: str,
    strategy: Literal["activity", "object", "otype", "length"],
    value: str | list[int],
    retain: bool = True,
) -> dict[str, Any]:
    """Connected-component filtering — the OCEL-specific power feature.

    Dispatches on ``strategy``:

    - ``"activity"`` — keep events in the connected component containing any
      object touched by activity ``value`` (string). ``retain`` is ignored.
    - ``"object"`` — keep events in the connected component containing the
      object with id ``value`` (string). ``retain`` is ignored.
    - ``"otype"`` — filter by the connected component of an object type.
      ``value`` is a string; ``retain`` controls keep-vs-drop.
    - ``"length"`` — keep CCs whose size is in ``[min, max]``. ``value`` is
      a two-element integer list ``[min, max]``. ``retain`` is ignored.

    PM4Py's CC filters are marked experimental; expect occasional edge-case
    failures on malformed OCELs.
    """
    if strategy not in _CC_STRATEGIES:
        raise UnsupportedFormat(
            f"Unknown cc strategy {strategy!r}. Expected one of {_CC_STRATEGIES}."
        )

    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)
    before = _counts(ocel)

    if strategy == "activity":
        if not isinstance(value, str):
            raise ValueError("strategy='activity' requires value to be a string (activity name)")
        filtered = pm4py.filter_ocel_cc_activity(ocel, value)
    elif strategy == "object":
        if not isinstance(value, str):
            raise ValueError("strategy='object' requires value to be a string (object id)")
        result = pm4py.filter_ocel_cc_object(ocel, value)
        # Signature allows a tuple return when return_conn_comp=True; default is OCEL.
        filtered = result[0] if isinstance(result, tuple) else result
    elif strategy == "otype":
        if not isinstance(value, str):
            raise ValueError("strategy='otype' requires value to be a string (object type)")
        filtered = pm4py.filter_ocel_cc_otype(ocel, value, positive=retain)
    else:  # "length"
        if not (
            isinstance(value, list) and len(value) == 2 and all(isinstance(v, int) for v in value)
        ):
            raise ValueError(
                "strategy='length' requires value to be a 2-element integer list [min, max]"
            )
        min_len, max_len = int(value[0]), int(value[1])
        if min_len < 0 or max_len < min_len:
            raise ValueError(f"Expected 0 <= min <= max for cc length, got [{min_len}, {max_len}]")
        filtered = pm4py.filter_ocel_cc_length(ocel, min_len, max_len)

    return _wrap(
        source_ocel_id=ocel_id,
        filtered=filtered,
        before=before,
        filter_name=f"filter_ocel_cc({strategy})",
    )


__all__ = [
    "filter_ocel_attribute",
    "filter_ocel_cc",
    "filter_ocel_object_types",
    "filter_ocel_time_range",
]
