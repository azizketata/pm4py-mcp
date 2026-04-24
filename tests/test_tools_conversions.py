"""Unit tests for 0.4.0's convert_model tool."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind
from pm4py_mcp.server import registry
from pm4py_mcp.tools.conversions import convert_model
from pm4py_mcp.tools.discovery import (
    discover_bpmn,
    discover_petri_net,
    discover_powl,
    discover_process_tree,
)
from tests.fixtures import tiny_log


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log())


# --- every supported (source, target) pair works end-to-end ---


def test_convert_tree_to_petri(log_id: str) -> None:
    tree_id = discover_process_tree(log_id)["tree_id"]
    result = convert_model(tree_id, target_kind="petri_net")
    assert result["new_kind"] == "petri_net"
    assert result["new_id"].startswith("pn-")
    assert result["source_id"] == tree_id
    assert result["source_kind"] == "process_tree"
    assert result["num_places"] > 0
    assert result["num_transitions"] > 0


def test_convert_bpmn_to_petri(log_id: str) -> None:
    bpmn_id = discover_bpmn(log_id)["bpmn_id"]
    result = convert_model(bpmn_id, target_kind="petri_net")
    assert result["new_kind"] == "petri_net"
    assert result["source_kind"] == "bpmn"


def test_convert_powl_to_petri(log_id: str) -> None:
    powl_id = discover_powl(log_id)["powl_id"]
    result = convert_model(powl_id, target_kind="petri_net")
    assert result["new_kind"] == "petri_net"
    assert result["source_kind"] == "powl"


def test_convert_petri_to_bpmn(log_id: str) -> None:
    pn_id = discover_petri_net(log_id)["petri_id"]
    result = convert_model(pn_id, target_kind="bpmn")
    assert result["new_kind"] == "bpmn"
    assert result["source_kind"] == "petri_net"
    assert result["num_nodes"] > 0


def test_convert_tree_to_bpmn(log_id: str) -> None:
    tree_id = discover_process_tree(log_id)["tree_id"]
    result = convert_model(tree_id, target_kind="bpmn")
    assert result["new_kind"] == "bpmn"
    assert result["source_kind"] == "process_tree"


def test_convert_petri_to_process_tree(log_id: str) -> None:
    pn_id = discover_petri_net(log_id)["petri_id"]
    result = convert_model(pn_id, target_kind="process_tree")
    assert result["new_kind"] == "process_tree"
    assert result["source_kind"] == "petri_net"
    assert result["num_nodes"] > 0


def test_convert_bpmn_to_process_tree(log_id: str) -> None:
    bpmn_id = discover_bpmn(log_id)["bpmn_id"]
    result = convert_model(bpmn_id, target_kind="process_tree")
    assert result["new_kind"] == "process_tree"
    assert result["source_kind"] == "bpmn"


def test_convert_powl_to_process_tree(log_id: str) -> None:
    powl_id = discover_powl(log_id)["powl_id"]
    result = convert_model(powl_id, target_kind="process_tree")
    assert result["new_kind"] == "process_tree"
    assert result["source_kind"] == "powl"


# --- lineage breadcrumb ---


def test_convert_stamps_source_handle_breadcrumb(log_id: str) -> None:
    tree_id = discover_process_tree(log_id)["tree_id"]
    new_pn = convert_model(tree_id, target_kind="petri_net")["new_id"]
    assert registry.source_handle(new_pn) == tree_id


def test_convert_chain_breadcrumbs_each_hop(log_id: str) -> None:
    """Multi-hop conversion preserves per-hop lineage."""
    pn_id = discover_petri_net(log_id)["petri_id"]
    bpmn_from_pn = convert_model(pn_id, target_kind="bpmn")["new_id"]
    tree_from_bpmn = convert_model(bpmn_from_pn, target_kind="process_tree")["new_id"]
    assert registry.source_handle(bpmn_from_pn) == pn_id
    assert registry.source_handle(tree_from_bpmn) == bpmn_from_pn


# --- error paths ---


def test_convert_unsupported_pair_raises(log_id: str) -> None:
    """A log_id is never a valid source for convert_model."""
    with pytest.raises(InvalidKind, match="Cannot convert"):
        convert_model(log_id, target_kind="petri_net")


def test_convert_unsupported_target_kind_raises(log_id: str) -> None:
    pn_id = discover_petri_net(log_id)["petri_id"]
    with pytest.raises(InvalidKind, match="Unsupported target_kind"):
        convert_model(pn_id, target_kind="log")  # type: ignore[arg-type]


def test_convert_missing_source_raises() -> None:
    with pytest.raises(HandleNotFound):
        convert_model("pn-nope", target_kind="bpmn")


def test_convert_bpmn_target_rejects_powl_source(log_id: str) -> None:
    """pm4py.convert_to_bpmn does NOT accept POWL directly in 2.7.22.2."""
    powl_id = discover_powl(log_id)["powl_id"]
    with pytest.raises(InvalidKind, match="Cannot convert"):
        convert_model(powl_id, target_kind="bpmn")
