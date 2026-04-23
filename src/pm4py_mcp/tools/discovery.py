"""Phase 1 — process-model discovery tools.

Each tool takes a ``log_id``, runs a PM4Py discovery algorithm, stores the
resulting model in the registry under a new handle, and returns a compact
summary. Models are never returned in-line — only the handle + a shape
description (counts of places / transitions / arcs / nodes).

The returned handle is consumed by ``visualize_*`` (Slice 3) and
``conformance_*`` (Slice 4) tools.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import pandas as pd
import pm4py

from pm4py_mcp.errors import UnsupportedFormat
from pm4py_mcp.server import mcp, registry

Algorithm = Literal["inductive", "heuristics", "alpha"]


@mcp.tool()
def discover_dfg(log_id: str) -> dict[str, Any]:
    """Discover the directly-follows graph (DFG) of an event log.

    Returns a handle for later rendering via ``visualize_dfg`` plus a
    shape summary (edge count, start/end activity counts).
    """
    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)

    dfg, start_activities, end_activities = pm4py.discover_dfg(log)
    payload = {
        "dfg": dfg,
        "start_activities": start_activities,
        "end_activities": end_activities,
    }
    dfg_id = registry.put("dfg", payload)

    return {
        "dfg_id": dfg_id,
        "log_id": log_id,
        "num_edges": len(dfg),
        "num_start_activities": len(start_activities),
        "num_end_activities": len(end_activities),
        "total_arc_frequency": sum(int(v) for v in dfg.values()),
    }


@mcp.tool()
def discover_petri_net(
    log_id: str,
    algorithm: Algorithm = "inductive",
    noise_threshold: float = 0.0,
) -> dict[str, Any]:
    """Discover a Petri net from an event log.

    ``algorithm`` dispatches to one of three PM4Py miners:

    - ``"inductive"`` (default) — Inductive Miner, sound-by-construction.
      Accepts ``noise_threshold`` in [0, 1] to prune infrequent behavior.
    - ``"heuristics"`` — Heuristics Miner, robust to noise.
    - ``"alpha"`` — classical Alpha Miner.

    Returns a handle to the (net, initial_marking, final_marking) triple
    plus structural counts. The model is stored with kind ``petri_net``.
    """
    if algorithm not in ("inductive", "heuristics", "alpha"):
        raise UnsupportedFormat(
            f"Unknown Petri-net algorithm {algorithm!r}. "
            f"Expected one of: 'inductive', 'heuristics', 'alpha'."
        )
    if not 0.0 <= noise_threshold <= 1.0:
        raise ValueError(f"noise_threshold must be in [0, 1], got {noise_threshold}")

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)

    if algorithm == "inductive":
        net, im, fm = pm4py.discover_petri_net_inductive(log, noise_threshold=noise_threshold)
    elif algorithm == "heuristics":
        net, im, fm = pm4py.discover_petri_net_heuristics(log)
    else:  # "alpha"
        net, im, fm = pm4py.discover_petri_net_alpha(log)

    petri_id = registry.put("petri_net", (net, im, fm))

    return {
        "petri_id": petri_id,
        "log_id": log_id,
        "algorithm": algorithm,
        "noise_threshold": noise_threshold if algorithm == "inductive" else None,
        "num_places": len(net.places),
        "num_transitions": len(net.transitions),
        "num_arcs": len(net.arcs),
    }


@mcp.tool()
def discover_process_tree(log_id: str, noise_threshold: float = 0.0) -> dict[str, Any]:
    """Discover a process tree via the Inductive Miner.

    Process trees compose cleanly and convert to Petri nets / BPMN. Returns
    a handle to the tree plus its structural shape.
    """
    if not 0.0 <= noise_threshold <= 1.0:
        raise ValueError(f"noise_threshold must be in [0, 1], got {noise_threshold}")

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)

    tree = pm4py.discover_process_tree_inductive(log, noise_threshold=noise_threshold)
    tree_id = registry.put("process_tree", tree)

    return {
        "tree_id": tree_id,
        "log_id": log_id,
        "noise_threshold": noise_threshold,
        "num_nodes": _count_tree_nodes(tree),
        "depth": _tree_depth(tree),
        "root_operator": str(tree.operator) if tree.operator is not None else None,
    }


@mcp.tool()
def discover_bpmn(log_id: str, noise_threshold: float = 0.0) -> dict[str, Any]:
    """Discover a BPMN diagram via the Inductive Miner.

    Convenience wrapper over ``discover_process_tree_inductive`` + BPMN
    conversion. Returns a handle plus node/flow counts.
    """
    if not 0.0 <= noise_threshold <= 1.0:
        raise ValueError(f"noise_threshold must be in [0, 1], got {noise_threshold}")

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)

    bpmn = pm4py.discover_bpmn_inductive(log, noise_threshold=noise_threshold)
    bpmn_id = registry.put("bpmn", bpmn)

    nodes = list(bpmn.get_nodes())
    flows = list(bpmn.get_flows())

    return {
        "bpmn_id": bpmn_id,
        "log_id": log_id,
        "noise_threshold": noise_threshold,
        "num_nodes": len(nodes),
        "num_flows": len(flows),
    }


# --- internals ---


def _count_tree_nodes(node: Any) -> int:
    """Recursively count process-tree nodes."""
    if not node.children:
        return 1
    return 1 + sum(_count_tree_nodes(c) for c in node.children)


def _tree_depth(node: Any) -> int:
    if not node.children:
        return 1
    return 1 + max(_tree_depth(c) for c in node.children)


__all__ = [
    "discover_bpmn",
    "discover_dfg",
    "discover_petri_net",
    "discover_process_tree",
]
