"""Unit tests for 0.4.1's simulate_log tool."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind
from pm4py_mcp.server import registry
from pm4py_mcp.tools.discovery import discover_petri_net, discover_process_tree
from pm4py_mcp.tools.io import describe_log
from pm4py_mcp.tools.simulation import simulate_log
from tests.fixtures import tiny_log


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log())


def test_simulate_from_petri_net_produces_log(log_id: str) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    result = simulate_log(petri_id, num_traces=10)
    assert result["log_id"].startswith("log-")
    assert result["source_model_id"] == petri_id
    assert result["source_kind"] == "petri_net"
    assert result["num_traces_requested"] == 10
    assert result["num_traces_produced"] == 10
    assert result["num_events"] > 0


def test_simulate_from_process_tree_produces_log(log_id: str) -> None:
    tree_id = discover_process_tree(log_id)["tree_id"]
    result = simulate_log(tree_id, num_traces=5)
    assert result["source_kind"] == "process_tree"
    assert result["num_traces_produced"] == 5


def test_simulated_log_composes_with_phase1_tools(log_id: str) -> None:
    """The whole point of simulate_log: output is a first-class log_id."""
    petri_id = discover_petri_net(log_id)["petri_id"]
    sim = simulate_log(petri_id, num_traces=3)
    # describe_log on the simulated handle must work
    described = describe_log(sim["log_id"])
    assert described["num_cases"] == 3
    assert described["num_events"] >= 3


def test_simulate_records_source_handle(log_id: str) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    sim = simulate_log(petri_id, num_traces=2)
    assert registry.source_handle(sim["log_id"]) == petri_id


def test_simulate_rejects_bpmn(log_id: str) -> None:
    from pm4py_mcp.tools.discovery import discover_bpmn

    bpmn_id = discover_bpmn(log_id)["bpmn_id"]
    with pytest.raises(InvalidKind, match="requires a petri_net or process_tree"):
        simulate_log(bpmn_id, num_traces=5)


def test_simulate_rejects_log(log_id: str) -> None:
    with pytest.raises(InvalidKind):
        simulate_log(log_id, num_traces=5)


def test_simulate_rejects_zero_traces(log_id: str) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    with pytest.raises(ValueError):
        simulate_log(petri_id, num_traces=0)


def test_simulate_rejects_excessive_traces(log_id: str) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    with pytest.raises(ValueError, match="safety cap"):
        simulate_log(petri_id, num_traces=100_000)


def test_simulate_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        simulate_log("pn-nope", num_traces=5)
