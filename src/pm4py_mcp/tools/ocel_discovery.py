"""Phase 2 Slice 2 — OCEL 2.0 discovery tools.

Both tools take an ``ocel_id`` and return a handle to a discovered
object-centric artifact plus a compact summary. Consume the handles with
``visualize_ocdfg`` / ``visualize_oc_petri_net``.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import pm4py
from pm4py.objects.ocel.obj import OCEL

from pm4py_mcp.errors import UnsupportedFormat
from pm4py_mcp.server import mcp, registry

_INDUCTIVE_VARIANTS = ("im", "imd")


@mcp.tool()
def discover_ocdfg(ocel_id: str) -> dict[str, Any]:
    """Discover an object-centric directly-follows graph (OC-DFG).

    Returns a handle for later rendering via ``visualize_ocdfg`` plus a
    shape summary: activity count, object types, and per-object-type edge
    counts (the "how many distinct activity pairs does this object type
    induce" signal).
    """
    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)

    dfg = pm4py.discover_ocdfg(ocel)
    ocdfg_id = registry.put("ocdfg", dfg)

    activities = sorted(dfg.get("activities", set()))
    object_types = sorted(dfg.get("object_types", set()))

    # ``edges`` is nested: {metric: {object_type: {(a1, a2): set_of_event_couples}}}
    edges_raw = dfg.get("edges", {}).get("event_couples", {})
    edges_per_type = {str(ot): len(edge_map) for ot, edge_map in edges_raw.items()}
    total_edges = sum(edges_per_type.values())

    return {
        "ocdfg_id": ocdfg_id,
        "source_ocel_id": ocel_id,
        "num_activities": len(activities),
        "activities": activities[:20],
        "num_object_types": len(object_types),
        "object_types": object_types,
        "edges_per_object_type": edges_per_type,
        "total_edges": total_edges,
    }


@mcp.tool()
def discover_oc_petri_net(
    ocel_id: str,
    variant: Literal["im", "imd"] = "im",
) -> dict[str, Any]:
    """Discover an object-centric Petri net (OCPN).

    ``variant`` dispatches the underlying Inductive Miner:

    - ``"im"`` (default) — classical Inductive Miner on each per-type projection
    - ``"imd"`` — Inductive Miner Directly-Follows (faster, less precise)

    Returns a handle to the OCPN plus per-object-type structural counts.
    """
    if variant not in _INDUCTIVE_VARIANTS:
        raise UnsupportedFormat(
            f"Unknown OCPN inductive variant {variant!r}. Expected one of {_INDUCTIVE_VARIANTS}."
        )

    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)

    ocpn = pm4py.discover_oc_petri_net(ocel, inductive_miner_variant=variant)
    ocpn_id = registry.put("ocpn", ocpn)

    # ocpn["petri_nets"] is {object_type: (net, initial_marking, final_marking)}
    per_type: dict[str, dict[str, int]] = {}
    for ot, triple in ocpn.get("petri_nets", {}).items():
        net, _im, _fm = triple
        per_type[str(ot)] = {
            "num_places": len(net.places),
            "num_transitions": len(net.transitions),
            "num_arcs": len(net.arcs),
        }

    total_places = sum(v["num_places"] for v in per_type.values())
    total_transitions = sum(v["num_transitions"] for v in per_type.values())
    total_arcs = sum(v["num_arcs"] for v in per_type.values())

    return {
        "ocpn_id": ocpn_id,
        "source_ocel_id": ocel_id,
        "variant": variant,
        "num_object_types": len(per_type),
        "object_types": sorted(per_type.keys()),
        "per_object_type": per_type,
        "total_places": total_places,
        "total_transitions": total_transitions,
        "total_arcs": total_arcs,
    }


__all__ = ["discover_oc_petri_net", "discover_ocdfg"]
