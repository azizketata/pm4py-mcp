"""Phase 2 Part 2 (0.4.0) — model conversions.

Wraps pm4py's three ``convert_to_*`` functions into a single dispatched tool
``convert_model(source_id, target_kind)``. Supported conversions (as of
pm4py 2.7.22.2):

- → ``petri_net``: from ``bpmn``, ``process_tree``, ``powl``
- → ``bpmn``: from ``petri_net``, ``process_tree``
- → ``process_tree``: from ``petri_net``, ``bpmn``, ``powl``

Unsupported pairs raise ``InvalidKind`` with a clear message. The new
handle's registry entry records the ``source_handle`` so conversion lineage
is debuggable via ``registry.source_handle()``.
"""

from __future__ import annotations

from typing import Any, Literal

import pm4py

from pm4py_mcp.errors import InvalidKind
from pm4py_mcp.server import mcp, registry

TargetKind = Literal["petri_net", "bpmn", "process_tree"]

# Which source kinds can convert to which target kinds.
_SUPPORTED: dict[TargetKind, set[str]] = {
    "petri_net": {"bpmn", "process_tree", "powl"},
    "bpmn": {"petri_net", "process_tree"},
    "process_tree": {"petri_net", "bpmn", "powl"},
}


def _summarize(kind: str, payload: Any) -> dict[str, int]:
    """Return a shape summary for the newly-created artifact."""
    if kind == "petri_net":
        net, _im, _fm = payload
        return {
            "num_places": len(net.places),
            "num_transitions": len(net.transitions),
            "num_arcs": len(net.arcs),
        }
    if kind == "bpmn":
        return {
            "num_nodes": len(list(payload.get_nodes())),
            "num_flows": len(list(payload.get_flows())),
        }
    # process_tree
    return {"num_nodes": _count_tree_nodes(payload)}


def _count_tree_nodes(node: Any) -> int:
    if not getattr(node, "children", None):
        return 1
    return 1 + sum(_count_tree_nodes(c) for c in node.children)


@mcp.tool()
def convert_model(source_id: str, target_kind: TargetKind) -> dict[str, Any]:
    """Convert a process model from one representation to another.

    ``source_id`` is any model handle (Petri net, BPMN, process tree, POWL).
    ``target_kind`` is one of ``"petri_net"``, ``"bpmn"``, ``"process_tree"``.

    Supported pairs:

    - → petri_net: from bpmn, process_tree, powl
    - → bpmn: from petri_net, process_tree
    - → process_tree: from petri_net, bpmn, powl

    Unsupported combinations raise ``InvalidKind``. The new handle records
    ``source_handle=source_id`` so lineage is debuggable.
    """
    if target_kind not in _SUPPORTED:
        raise InvalidKind(
            f"Unsupported target_kind {target_kind!r}. Expected one of {sorted(_SUPPORTED)}."
        )

    source_kind, source_payload = registry.get(source_id)
    allowed = _SUPPORTED[target_kind]
    if source_kind not in allowed:
        raise InvalidKind(
            f"Cannot convert {source_kind!r} to {target_kind!r}. "
            f"→ {target_kind} accepts sources: {sorted(allowed)}."
        )

    # Petri net payloads are stored as (net, im, fm) tuples; pm4py's
    # convert_to_* functions take positional args, so tuples must be unpacked.
    if source_kind == "petri_net":
        args: tuple[Any, ...] = tuple(source_payload)
    else:
        args = (source_payload,)

    if target_kind == "petri_net":
        net, im, fm = pm4py.convert_to_petri_net(*args)
        new_payload: Any = (net, im, fm)
    elif target_kind == "bpmn":
        new_payload = pm4py.convert_to_bpmn(*args)
    else:  # process_tree
        new_payload = pm4py.convert_to_process_tree(*args)

    new_id = registry.put(target_kind, new_payload, source_handle=source_id)

    return {
        "new_id": new_id,
        "new_kind": target_kind,
        "source_id": source_id,
        "source_kind": source_kind,
        **_summarize(target_kind, new_payload),
    }


__all__ = ["convert_model"]
