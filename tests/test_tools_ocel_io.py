"""Phase 2 Slice 1 — OCEL I/O tool unit tests.

The marquee test is ``test_flatten_bridge_composes_with_phase1_discover`` —
it asserts that the Phase 2 handle chain ``load_ocel → flatten_ocel`` produces
a ``log_id`` that Phase 1's ``discover_petri_net`` accepts and discovers a
non-trivial model from. This is Slice 1's architectural gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind, UnsupportedFormat
from pm4py_mcp.server import registry
from pm4py_mcp.tools.discovery import discover_petri_net
from pm4py_mcp.tools.ocel_io import (
    describe_ocel,
    export_ocel,
    flatten_ocel,
    load_ocel,
)
from tests.fixtures import tiny_ocel, tiny_ocel_file


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


# --- load_ocel ---


def test_load_ocel_returns_summary_and_handle(tmp_path: Path) -> None:
    ocel_path = tiny_ocel_file(tmp_path)
    summary = load_ocel(str(ocel_path))

    assert summary["ocel_id"].startswith("ocel-")
    assert summary["num_events"] == 10
    assert summary["num_objects"] == 8
    assert summary["num_object_types"] == 3
    assert set(summary["object_types"]) == {"order", "item", "delivery"}
    assert summary["num_activities"] == 4
    assert set(summary["activities_preview"]) == {"Place Order", "Pick Item", "Ship", "Deliver"}
    # Events-per-type sanity: order touches 8 events (all except Deliver), item touches 4, delivery 4
    epot = summary["events_per_object_type"]
    assert epot["order"] == 8
    assert epot["item"] == 4
    assert epot["delivery"] == 4
    assert summary["format"] == "jsonocel"
    assert summary["ocel_id"] in registry


def test_load_ocel_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_ocel("/nonexistent/path/to/file.jsonocel")


def test_load_ocel_unknown_extension_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "log.weird"
    bogus.write_text("{}")
    with pytest.raises(UnsupportedFormat):
        load_ocel(str(bogus))


def test_load_ocel_bundled_example_works() -> None:
    """The committed examples/order-management.jsonocel must load cleanly."""
    bundled = Path(__file__).resolve().parent.parent / "examples" / "order-management.jsonocel"
    if not bundled.is_file():
        pytest.skip("bundled example OCEL not present")
    summary = load_ocel(str(bundled))
    assert summary["num_events"] >= 10
    assert summary["num_object_types"] == 3


# --- describe_ocel ---


def test_describe_ocel_matches_load_summary(tmp_path: Path) -> None:
    ocel_path = tiny_ocel_file(tmp_path)
    load_summary = load_ocel(str(ocel_path))
    desc_summary = describe_ocel(load_summary["ocel_id"])

    # describe_ocel doesn't set 'format'; that's only in load_ocel response
    expected = {k: v for k, v in load_summary.items() if k != "format"}
    assert desc_summary == expected


def test_describe_ocel_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        describe_ocel("ocel-doesnotexist")


def test_describe_ocel_wrong_kind_raises() -> None:
    h = registry.put("log", object())
    with pytest.raises(InvalidKind):
        describe_ocel(h)


# --- flatten_ocel (the bridge) ---


def test_flatten_ocel_returns_log_handle_and_counts() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = flatten_ocel(ocel_id, object_type="order")

    assert result["log_id"].startswith("log-")
    assert result["source_ocel_id"] == ocel_id
    assert result["object_type"] == "order"
    # Flattening on 'order' drops Deliver events (only touches delivery objects)
    assert result["num_cases"] == 2
    assert result["num_events"] == 8


def test_flatten_ocel_each_object_type() -> None:
    """Every OCEL object type should flatten to a non-empty traditional log."""
    ocel_id = registry.put("ocel", tiny_ocel())
    for otype, expected_cases in (("order", 2), ("item", 4), ("delivery", 2)):
        result = flatten_ocel(ocel_id, object_type=otype)
        assert result["num_cases"] == expected_cases, otype
        assert result["num_events"] > 0


def test_flatten_ocel_unknown_object_type_raises() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    with pytest.raises(UnsupportedFormat) as exc_info:
        flatten_ocel(ocel_id, object_type="customer")
    # Error message should list valid object types so the LLM can recover
    assert "order" in str(exc_info.value)
    assert "item" in str(exc_info.value)


def test_flatten_ocel_wrong_kind_raises() -> None:
    h = registry.put("log", object())
    with pytest.raises(InvalidKind):
        flatten_ocel(h, object_type="order")


def test_flatten_bridge_composes_with_phase1_discover() -> None:
    """Slice 1 gate: OCEL -> flatten -> Phase 1 discover_petri_net must work."""
    ocel_id = registry.put("ocel", tiny_ocel())
    flat = flatten_ocel(ocel_id, object_type="order")
    log_id = flat["log_id"]

    # Phase 1 tool accepts the Phase 2 handle. This is the whole point of Phase 2.
    petri_result = discover_petri_net(log_id, algorithm="inductive", noise_threshold=0.0)
    assert petri_result["petri_id"].startswith("pn-")
    assert petri_result["num_places"] >= 2  # at least source + sink
    assert petri_result["num_transitions"] >= 1


# --- export_ocel ---


def test_export_ocel_jsonocel_to_workspace() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = export_ocel(ocel_id, format="jsonocel", path="exported")
    out = Path(result["path"])

    assert out.exists()
    assert out.suffix == ".jsonocel"
    assert result["format"] == "jsonocel"
    assert result["size_bytes"] > 0


def test_export_ocel_absolute_path_honored(tmp_path: Path) -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    target = tmp_path / "nested" / "out"
    result = export_ocel(ocel_id, format="jsonocel", path=str(target))
    out = Path(result["path"])
    assert out.is_relative_to(tmp_path)
    assert out.exists()


def test_export_ocel_roundtrip_preserves_shape(tmp_path: Path) -> None:
    """Write and re-read — the new OCEL should have the same event/object counts."""
    ocel_id = registry.put("ocel", tiny_ocel())
    out = tmp_path / "roundtrip.jsonocel"
    export_ocel(ocel_id, format="jsonocel", path=str(out))

    reloaded = load_ocel(str(out))
    assert reloaded["num_events"] == 10
    assert reloaded["num_objects"] == 8
    assert reloaded["num_object_types"] == 3


def test_export_ocel_unsupported_format() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    with pytest.raises(UnsupportedFormat):
        export_ocel(ocel_id, format="xes", path="out")


def test_export_ocel_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        export_ocel("ocel-gone", format="jsonocel", path="x")


def test_export_ocel_wrong_kind_raises() -> None:
    h = registry.put("log", object())
    with pytest.raises(InvalidKind):
        export_ocel(h, format="jsonocel", path="x")
