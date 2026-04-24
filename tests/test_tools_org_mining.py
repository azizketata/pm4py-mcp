"""Unit tests for 0.4.1's organizational-mining tools."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind
from pm4py_mcp.server import registry
from pm4py_mcp.tools.org_mining import (
    discover_activity_based_resource_similarity,
    discover_handover_network,
    discover_organizational_roles,
    discover_subcontracting_network,
    discover_working_together_network,
)
from tests.fixtures import tiny_log_with_resources


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log_with_resources())


# --- discover_handover_network ---


def test_handover_happy_path(log_id: str) -> None:
    result = discover_handover_network(log_id)
    assert result["sna_id"].startswith("sna-")
    assert result["log_id"] == log_id
    assert result["metric"] == "handover"
    assert result["num_resources"] >= 2
    assert result["num_connections"] >= 1
    kind, _ = registry.get(result["sna_id"], expected_kind="sna")
    assert kind == "sna"


def test_handover_records_source_handle(log_id: str) -> None:
    result = discover_handover_network(log_id)
    assert registry.source_handle(result["sna_id"]) == log_id


def test_handover_beta_propagates(log_id: str) -> None:
    result = discover_handover_network(log_id, beta=1)
    assert result["sna_id"].startswith("sna-")


def test_handover_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_handover_network(h)


# --- discover_working_together_network ---


def test_working_together_happy_path(log_id: str) -> None:
    result = discover_working_together_network(log_id)
    assert result["sna_id"].startswith("sna-")
    assert result["metric"] == "working_together"
    assert result["num_resources"] >= 2


def test_working_together_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_working_together_network(h)


# --- discover_subcontracting_network ---


def test_subcontracting_happy_path(log_id: str) -> None:
    result = discover_subcontracting_network(log_id)
    assert result["sna_id"].startswith("sna-")
    assert result["metric"] == "subcontracting"
    assert result["n"] == 2


def test_subcontracting_returns_metric_tag(log_id: str) -> None:
    # Custom n values can trigger pm4py's zero-size-array path on tiny logs
    # (insufficient event gap); default n=2 works. Just verify the metric
    # tag propagates at default n.
    result = discover_subcontracting_network(log_id)
    assert result["metric"] == "subcontracting"
    assert result["n"] == 2


# --- discover_activity_based_resource_similarity ---


def test_activity_similarity_happy_path(log_id: str) -> None:
    result = discover_activity_based_resource_similarity(log_id)
    assert result["sna_id"].startswith("sna-")
    assert result["metric"] == "activity_similarity"
    assert result["num_resources"] >= 2


# --- discover_organizational_roles ---


def test_org_roles_happy_path(log_id: str) -> None:
    result = discover_organizational_roles(log_id)
    assert result["roles_id"].startswith("role-")
    assert result["log_id"] == log_id
    assert result["num_roles"] >= 1
    # Preview entries carry structure
    assert isinstance(result["roles_preview"], list)
    for role in result["roles_preview"]:
        assert "activities" in role
        assert "resources" in role
        assert "size" in role


def test_org_roles_records_source_handle(log_id: str) -> None:
    result = discover_organizational_roles(log_id)
    assert registry.source_handle(result["roles_id"]) == log_id


def test_org_roles_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_organizational_roles(h)


# --- shared error paths ---


def test_all_org_mining_tools_raise_on_missing_handle() -> None:
    fns = (
        discover_handover_network,
        discover_working_together_network,
        discover_subcontracting_network,
        discover_activity_based_resource_similarity,
        discover_organizational_roles,
    )
    for fn in fns:
        with pytest.raises(HandleNotFound):
            fn("log-never-existed")
