"""Slice 3 — discovery tool unit tests (no Graphviz required)."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind, UnsupportedFormat
from pm4py_mcp.server import registry
from pm4py_mcp.tools.discovery import (
    discover_bpmn,
    discover_declare,
    discover_dfg,
    discover_log_skeleton,
    discover_petri_net,
    discover_powl,
    discover_process_tree,
    discover_temporal_profile,
)
from tests.fixtures import tiny_log


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log())


# --- discover_dfg ---


def test_discover_dfg_returns_handle_and_shape(log_id: str) -> None:
    result = discover_dfg(log_id)
    assert result["dfg_id"].startswith("dfg-")
    assert result["log_id"] == log_id
    # The tiny log has 4 activities with 3 activity-to-activity edges:
    # register→triage, triage→treat, treat→discharge
    assert result["num_edges"] == 3
    assert result["num_start_activities"] == 1
    # discharge x2 (cases 1,2) + treat x1 (case 3) = 2 distinct end activities
    assert result["num_end_activities"] == 2
    # Total frequency = 3 register->triage + 3 triage->treat + 2 treat->discharge = 8
    assert result["total_arc_frequency"] == 8
    # Stored artifact resolves
    kind, _payload = registry.get(result["dfg_id"], expected_kind="dfg")
    assert kind == "dfg"


def test_discover_dfg_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        discover_dfg("log-gone")


# --- discover_petri_net ---


def test_discover_petri_net_inductive_default(log_id: str) -> None:
    result = discover_petri_net(log_id)
    assert result["petri_id"].startswith("pn-")
    assert result["algorithm"] == "inductive"
    assert result["noise_threshold"] == 0.0
    assert result["num_places"] >= 2  # at least source + sink
    assert result["num_transitions"] >= 1
    assert result["num_arcs"] >= 2


def test_discover_petri_net_heuristics(log_id: str) -> None:
    result = discover_petri_net(log_id, algorithm="heuristics")
    assert result["algorithm"] == "heuristics"
    assert result["noise_threshold"] is None  # heuristics ignores the param
    assert result["num_places"] >= 1


def test_discover_petri_net_alpha(log_id: str) -> None:
    result = discover_petri_net(log_id, algorithm="alpha")
    assert result["algorithm"] == "alpha"
    assert result["noise_threshold"] is None
    assert result["num_places"] >= 1


def test_discover_petri_net_rejects_unknown_algorithm(log_id: str) -> None:
    with pytest.raises(UnsupportedFormat):
        discover_petri_net(log_id, algorithm="nonsense")  # type: ignore[arg-type]


def test_discover_petri_net_rejects_bad_noise_threshold(log_id: str) -> None:
    with pytest.raises(ValueError):
        discover_petri_net(log_id, noise_threshold=1.5)
    with pytest.raises(ValueError):
        discover_petri_net(log_id, noise_threshold=-0.1)


def test_discover_petri_net_kind_is_petri(log_id: str) -> None:
    result = discover_petri_net(log_id)
    kind, payload = registry.get(result["petri_id"])
    assert kind == "petri_net"
    _net, im, _fm = payload
    # Initial marking should have at least one token
    assert sum(im.values()) >= 1


# --- discover_process_tree ---


def test_discover_process_tree(log_id: str) -> None:
    result = discover_process_tree(log_id)
    assert result["tree_id"].startswith("pt-")
    assert result["num_nodes"] >= 1
    assert result["depth"] >= 1
    kind, _tree = registry.get(result["tree_id"])
    assert kind == "process_tree"


def test_discover_process_tree_rejects_bad_threshold(log_id: str) -> None:
    with pytest.raises(ValueError):
        discover_process_tree(log_id, noise_threshold=2.0)


# --- discover_bpmn ---


def test_discover_bpmn(log_id: str) -> None:
    result = discover_bpmn(log_id)
    assert result["bpmn_id"].startswith("bpmn-")
    assert result["num_nodes"] >= 1
    assert result["num_flows"] >= 1
    kind, _bpmn = registry.get(result["bpmn_id"])
    assert kind == "bpmn"


def test_discover_bpmn_rejects_bad_threshold(log_id: str) -> None:
    with pytest.raises(ValueError):
        discover_bpmn(log_id, noise_threshold=-0.5)


# --- cross-tool: discovery results compose with visualization kinds ---


def test_handles_are_distinct_across_kinds(log_id: str) -> None:
    """Every discovery tool mints a handle with its own kind prefix."""
    dfg_id = discover_dfg(log_id)["dfg_id"]
    pn_id = discover_petri_net(log_id)["petri_id"]
    tree_id = discover_process_tree(log_id)["tree_id"]
    bpmn_id = discover_bpmn(log_id)["bpmn_id"]

    assert dfg_id.startswith("dfg-")
    assert pn_id.startswith("pn-")
    assert tree_id.startswith("pt-")
    assert bpmn_id.startswith("bpmn-")
    assert len({dfg_id, pn_id, tree_id, bpmn_id}) == 4


# --- 0.4.0: advanced discovery ---


def test_discover_declare_happy_path(log_id: str) -> None:
    result = discover_declare(log_id)
    assert result["declare_id"].startswith("decl-")
    assert result["log_id"] == log_id
    assert result["num_templates"] > 0
    assert result["num_constraints"] >= 0
    assert isinstance(result["templates_preview"], list)
    # Artifact is reachable under declare kind
    kind, payload = registry.get(result["declare_id"], expected_kind="declare")
    assert kind == "declare"
    assert isinstance(payload, dict)


def test_discover_declare_records_source_handle(log_id: str) -> None:
    result = discover_declare(log_id)
    assert registry.source_handle(result["declare_id"]) == log_id


def test_discover_declare_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_declare(h)


def test_discover_declare_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        discover_declare("log-nope")


def test_discover_log_skeleton_happy_path(log_id: str) -> None:
    result = discover_log_skeleton(log_id)
    assert result["log_skeleton_id"].startswith("lsk-")
    assert result["log_id"] == log_id
    assert result["noise_threshold"] == 0.0
    assert result["num_constraint_types"] > 0
    assert isinstance(result["constraints_per_type"], dict)


def test_discover_log_skeleton_records_source_handle(log_id: str) -> None:
    result = discover_log_skeleton(log_id)
    assert registry.source_handle(result["log_skeleton_id"]) == log_id


def test_discover_log_skeleton_rejects_bad_noise(log_id: str) -> None:
    with pytest.raises(ValueError):
        discover_log_skeleton(log_id, noise_threshold=1.5)


def test_discover_log_skeleton_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_log_skeleton(h)


def test_discover_powl_happy_path(log_id: str) -> None:
    result = discover_powl(log_id)
    assert result["powl_id"].startswith("powl-")
    assert result["log_id"] == log_id
    assert isinstance(result["root_operator"], str)
    assert result["num_children"] >= 0
    kind, _ = registry.get(result["powl_id"], expected_kind="powl")
    assert kind == "powl"


def test_discover_powl_records_source_handle(log_id: str) -> None:
    result = discover_powl(log_id)
    assert registry.source_handle(result["powl_id"]) == log_id


def test_discover_powl_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_powl(h)


def test_discover_temporal_profile_happy_path(log_id: str) -> None:
    result = discover_temporal_profile(log_id)
    assert result["temporal_profile_id"].startswith("tprof-")
    assert result["log_id"] == log_id
    assert result["num_pairs"] >= 0
    kind, payload = registry.get(result["temporal_profile_id"], expected_kind="temporal_profile")
    assert kind == "temporal_profile"
    # The stored dict has Tuple[str, str] keys; confirm that shape
    if payload:
        k = next(iter(payload.keys()))
        assert isinstance(k, tuple)
        assert len(k) == 2
        assert all(isinstance(s, str) for s in k)


def test_discover_temporal_profile_records_source_handle(log_id: str) -> None:
    result = discover_temporal_profile(log_id)
    assert registry.source_handle(result["temporal_profile_id"]) == log_id


def test_discover_temporal_profile_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        discover_temporal_profile(h)


def test_all_new_discovery_tools_raise_on_missing_handle() -> None:
    for fn in (
        discover_declare,
        discover_log_skeleton,
        discover_powl,
        discover_temporal_profile,
    ):
        with pytest.raises(HandleNotFound):
            fn("log-never-existed")
