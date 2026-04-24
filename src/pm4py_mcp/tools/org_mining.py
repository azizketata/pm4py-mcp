"""Phase 2 Part 2 (0.4.1) — organizational mining.

Five discovery tools that operate on event logs with a ``resource_key``
column (default ``"org:resource"``) and return either a social-network
(``SNA``) object or a list of ``Role`` clusters. Each SNA result is stored
under the ``"sna"`` registry kind; the role list under ``"org_roles"``.

Use these with ``abstract_sna`` (prose description of the network) and,
once 0.5.0 lands a matplotlib-backed SNA renderer, ``visualize_sna``.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
import pm4py

from pm4py_mcp.server import mcp, registry


def _get_log(log_id: str) -> pd.DataFrame:
    _, log_obj = registry.get(log_id, expected_kind="log")
    return cast(pd.DataFrame, log_obj)


def _sna_summary(sna: Any) -> dict[str, int]:
    """Return a compact shape summary for an SNA result."""
    conns = getattr(sna, "connections", {}) or {}
    resources = {r for pair in conns.keys() for r in pair}
    return {
        "num_resources": len(resources),
        "num_connections": len(conns),
    }


@mcp.tool()
def discover_handover_network(
    log_id: str,
    beta: int = 0,
    resource_key: str = "org:resource",
) -> dict[str, Any]:
    """Discover the handover-of-work network.

    An edge A → B means resource A's activity was directly followed by
    resource B's activity within the same case. ``beta`` controls distance
    decay (0 = direct handover only; larger values weigh indirect handoffs).

    Returns a handle under the ``"sna"`` kind plus resource / connection counts.
    """
    log = _get_log(log_id)
    sna = pm4py.discover_handover_of_work_network(log, beta=beta, resource_key=resource_key)
    sna_id = registry.put("sna", sna, source_handle=log_id)
    return {
        "sna_id": sna_id,
        "log_id": log_id,
        "metric": "handover",
        "resource_key": resource_key,
        **_sna_summary(sna),
    }


@mcp.tool()
def discover_working_together_network(
    log_id: str,
    resource_key: str = "org:resource",
) -> dict[str, Any]:
    """Discover the working-together network.

    An edge A ↔ B means resources A and B participated in the same case at
    least once. Captures collaboration patterns independent of order.
    """
    log = _get_log(log_id)
    sna = pm4py.discover_working_together_network(log, resource_key=resource_key)
    sna_id = registry.put("sna", sna, source_handle=log_id)
    return {
        "sna_id": sna_id,
        "log_id": log_id,
        "metric": "working_together",
        "resource_key": resource_key,
        **_sna_summary(sna),
    }


@mcp.tool()
def discover_subcontracting_network(
    log_id: str,
    n: int = 2,
    resource_key: str = "org:resource",
) -> dict[str, Any]:
    """Discover the subcontracting network.

    An edge A → B means: A did something, then within ``n`` events B did
    something, then A resumed. Captures "A hands off briefly to B and takes
    over again" patterns.
    """
    log = _get_log(log_id)
    sna = pm4py.discover_subcontracting_network(log, n=n, resource_key=resource_key)
    sna_id = registry.put("sna", sna, source_handle=log_id)
    return {
        "sna_id": sna_id,
        "log_id": log_id,
        "metric": "subcontracting",
        "n": n,
        "resource_key": resource_key,
        **_sna_summary(sna),
    }


@mcp.tool()
def discover_activity_based_resource_similarity(
    log_id: str,
    activity_key: str = "concept:name",
    resource_key: str = "org:resource",
) -> dict[str, Any]:
    """Discover the activity-based resource-similarity network.

    An edge A ↔ B weighted by how similar the activity profiles of A and B
    are. Captures "who does similar kinds of work" — complements handover
    by showing skill/role overlap.
    """
    log = _get_log(log_id)
    sna = pm4py.discover_activity_based_resource_similarity(
        log, activity_key=activity_key, resource_key=resource_key
    )
    sna_id = registry.put("sna", sna, source_handle=log_id)
    return {
        "sna_id": sna_id,
        "log_id": log_id,
        "metric": "activity_similarity",
        "activity_key": activity_key,
        "resource_key": resource_key,
        **_sna_summary(sna),
    }


@mcp.tool()
def discover_organizational_roles(
    log_id: str,
    activity_key: str = "concept:name",
    resource_key: str = "org:resource",
) -> dict[str, Any]:
    """Discover organizational roles — activity-sharing clusters of resources.

    pm4py returns a ``List[Role]`` where each role has:
    - ``activities``: list of activities that cluster together
    - ``originator_importance``: dict mapping resource → weight within the role

    Returns a handle under ``"org_roles"`` plus counts and a preview of the
    top 5 roles by importance sum.
    """
    log = _get_log(log_id)
    roles = pm4py.discover_organizational_roles(
        log, activity_key=activity_key, resource_key=resource_key
    )
    roles_id = registry.put("org_roles", roles, source_handle=log_id)

    def _role_size(r: Any) -> int:
        return int(sum((r.originator_importance or {}).values()) or 0)

    sorted_roles = sorted(roles, key=_role_size, reverse=True)
    preview = [
        {
            "activities": list(r.activities) if r.activities else [],
            "resources": list((r.originator_importance or {}).keys()),
            "size": _role_size(r),
        }
        for r in sorted_roles[:5]
    ]
    return {
        "roles_id": roles_id,
        "log_id": log_id,
        "num_roles": len(roles),
        "roles_preview": preview,
    }


__all__ = [
    "discover_activity_based_resource_similarity",
    "discover_handover_network",
    "discover_organizational_roles",
    "discover_subcontracting_network",
    "discover_working_together_network",
]
