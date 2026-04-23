"""Phase 2 Slice 2 — OCEL discovery tool unit tests."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind, UnsupportedFormat
from pm4py_mcp.server import registry
from pm4py_mcp.tools.ocel_discovery import (
    discover_oc_petri_net,
    discover_ocdfg,
)
from tests.fixtures import tiny_ocel


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def ocel_id() -> str:
    return registry.put("ocel", tiny_ocel())


# --- discover_ocdfg ---


def test_discover_ocdfg_returns_handle_and_summary(ocel_id: str) -> None:
    result = discover_ocdfg(ocel_id)
    assert result["ocdfg_id"].startswith("ocdfg-")
    assert result["source_ocel_id"] == ocel_id
    # tiny_ocel has 4 activities: Place Order, Pick Item, Ship, Deliver
    assert result["num_activities"] == 4
    assert set(result["activities"]) == {"Place Order", "Pick Item", "Ship", "Deliver"}
    # 3 object types
    assert result["num_object_types"] == 3
    assert set(result["object_types"]) == {"order", "item", "delivery"}
    # Each object type induces edges
    assert result["edges_per_object_type"].keys() == {"order", "item", "delivery"} - {"item"} | {
        "order",
        "delivery",
    }
    # 'item' object type has no sequential DFG edges in our fixture (items only appear once each)
    # but 'order' and 'delivery' do
    assert result["edges_per_object_type"].get("order", 0) >= 2
    assert result["total_edges"] >= 2


def test_discover_ocdfg_stored_artifact_is_dict(ocel_id: str) -> None:
    result = discover_ocdfg(ocel_id)
    kind, payload = registry.get(result["ocdfg_id"])
    assert kind == "ocdfg"
    # The stored artifact is the raw pm4py dict
    assert "activities" in payload
    assert "object_types" in payload
    assert "edges" in payload


def test_discover_ocdfg_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        discover_ocdfg("ocel-gone")


def test_discover_ocdfg_wrong_kind_raises() -> None:
    h = registry.put("log", object())
    with pytest.raises(InvalidKind):
        discover_ocdfg(h)


# --- discover_oc_petri_net ---


def test_discover_oc_petri_net_default_variant(ocel_id: str) -> None:
    result = discover_oc_petri_net(ocel_id)
    assert result["ocpn_id"].startswith("ocpn-")
    assert result["source_ocel_id"] == ocel_id
    assert result["variant"] == "im"
    assert result["num_object_types"] == 3
    assert set(result["object_types"]) == {"order", "item", "delivery"}
    # Per-type structural counts
    per_type = result["per_object_type"]
    for ot in ("order", "item", "delivery"):
        assert per_type[ot]["num_places"] >= 1
        assert per_type[ot]["num_transitions"] >= 1
        assert per_type[ot]["num_arcs"] >= 1
    # Totals consistent with the per-type breakdown
    assert result["total_places"] == sum(v["num_places"] for v in per_type.values())
    assert result["total_transitions"] == sum(v["num_transitions"] for v in per_type.values())
    assert result["total_arcs"] == sum(v["num_arcs"] for v in per_type.values())


def test_discover_oc_petri_net_imd_variant(ocel_id: str) -> None:
    result = discover_oc_petri_net(ocel_id, variant="imd")
    assert result["variant"] == "imd"
    assert result["num_object_types"] == 3


def test_discover_oc_petri_net_unknown_variant_raises(ocel_id: str) -> None:
    with pytest.raises(UnsupportedFormat):
        discover_oc_petri_net(ocel_id, variant="alpha")  # type: ignore[arg-type]


def test_discover_oc_petri_net_stored_artifact_is_ocpn(ocel_id: str) -> None:
    result = discover_oc_petri_net(ocel_id)
    kind, ocpn = registry.get(result["ocpn_id"])
    assert kind == "ocpn"
    # OCPetriNet exposes petri_nets, object_types, places, arcs
    assert "petri_nets" in ocpn
    assert "object_types" in ocpn
    assert set(ocpn["petri_nets"].keys()) == {"order", "item", "delivery"}


def test_discover_oc_petri_net_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        discover_oc_petri_net("ocel-gone")


def test_discover_oc_petri_net_wrong_kind_raises() -> None:
    h = registry.put("log", object())
    with pytest.raises(InvalidKind):
        discover_oc_petri_net(h)


# --- handles across kinds ---


def test_handles_are_distinct_across_ocel_kinds(ocel_id: str) -> None:
    """Each OCEL-discovery tool mints a handle with its own kind prefix."""
    ocdfg_id = discover_ocdfg(ocel_id)["ocdfg_id"]
    ocpn_id = discover_oc_petri_net(ocel_id)["ocpn_id"]

    assert ocdfg_id.startswith("ocdfg-")
    assert ocpn_id.startswith("ocpn-")
    assert len({ocel_id, ocdfg_id, ocpn_id}) == 3
