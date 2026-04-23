"""Phase 2 Slice 3 — OCEL filter tool unit tests.

Every filter is pure: each call mints a fresh ``ocel_id``, leaves the source
OCEL untouched. These tests assert the invariant (distinct new handle,
original OCEL still registered as ``ocel`` kind) plus the four dispatch paths
for each consolidated tool.
"""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind, UnsupportedFormat
from pm4py_mcp.server import registry
from pm4py_mcp.tools.ocel_filters import (
    filter_ocel_attribute,
    filter_ocel_cc,
    filter_ocel_object_types,
    filter_ocel_time_range,
)
from tests.fixtures import tiny_ocel


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def ocel_id() -> str:
    return registry.put("ocel", tiny_ocel())


# --- filter_ocel_time_range ---


def test_filter_ocel_time_range_window_includes_all(ocel_id: str) -> None:
    result = filter_ocel_time_range(
        ocel_id,
        start="2024-01-01T00:00:00",
        end="2024-01-02T00:00:00",
    )
    # All 10 events within the window.
    assert result["num_events_before"] == 10
    assert result["num_events_after"] == 10
    assert result["new_ocel_id"] != ocel_id
    assert result["new_ocel_id"].startswith("ocel-")


def test_filter_ocel_time_range_narrow_window_reduces(ocel_id: str) -> None:
    # 08:00-08:45 covers e01-e03 only (3 events).
    result = filter_ocel_time_range(
        ocel_id,
        start="2024-01-01T08:00:00",
        end="2024-01-01T08:45:00",
    )
    assert result["num_events_before"] == 10
    assert result["num_events_after"] < 10
    assert result["num_events_after"] >= 1


def test_filter_ocel_time_range_accepts_space_separator(ocel_id: str) -> None:
    """Normalize should accept pm4py's native 'YYYY-MM-DD HH:MM:SS' format too."""
    result = filter_ocel_time_range(
        ocel_id,
        start="2024-01-01 08:00:00",
        end="2024-01-01 08:45:00",
    )
    assert result["num_events_after"] >= 1


# --- filter_ocel_attribute ---


def test_filter_ocel_attribute_event_level_keep(ocel_id: str) -> None:
    # Keep only events where activity is "Pick Item" -> 4 events
    result = filter_ocel_attribute(
        ocel_id,
        attribute="ocel:activity",
        values=["Pick Item"],
        level="event",
        retain=True,
    )
    assert result["num_events_after"] == 4
    assert result["filter"] == "filter_ocel_attribute(event)"


def test_filter_ocel_attribute_event_level_drop(ocel_id: str) -> None:
    result = filter_ocel_attribute(
        ocel_id,
        attribute="ocel:activity",
        values=["Pick Item"],
        level="event",
        retain=False,
    )
    # Dropped 4 Pick-Item events out of 10
    assert result["num_events_after"] == 10 - 4


def test_filter_ocel_attribute_object_level(ocel_id: str) -> None:
    # Filter objects by their ocel:type -> keep only "order" objects
    result = filter_ocel_attribute(
        ocel_id,
        attribute="ocel:type",
        values=["order"],
        level="object",
        retain=True,
    )
    # 2 order objects out of 8 total
    assert result["num_objects_after"] == 2
    assert result["filter"] == "filter_ocel_attribute(object)"


def test_filter_ocel_attribute_rejects_empty_values(ocel_id: str) -> None:
    with pytest.raises(ValueError):
        filter_ocel_attribute(ocel_id, attribute="ocel:activity", values=[])


def test_filter_ocel_attribute_rejects_unknown_level(ocel_id: str) -> None:
    with pytest.raises(UnsupportedFormat):
        filter_ocel_attribute(
            ocel_id,
            attribute="ocel:activity",
            values=["Ship"],
            level="trace",  # type: ignore[arg-type]
        )


# --- filter_ocel_object_types ---


def test_filter_ocel_object_types_keep(ocel_id: str) -> None:
    result = filter_ocel_object_types(ocel_id, types=["order"], retain=True)
    # Only order objects remain (2 of 8)
    assert result["num_objects_after"] == 2
    assert result["new_ocel_id"] != ocel_id


def test_filter_ocel_object_types_drop(ocel_id: str) -> None:
    result = filter_ocel_object_types(ocel_id, types=["item"], retain=False)
    # 8 - 4 items = 4 objects remain
    assert result["num_objects_after"] == 4


def test_filter_ocel_object_types_rejects_empty(ocel_id: str) -> None:
    with pytest.raises(ValueError):
        filter_ocel_object_types(ocel_id, types=[])


# --- filter_ocel_cc (all four strategies) ---


def test_filter_ocel_cc_activity(ocel_id: str) -> None:
    result = filter_ocel_cc(ocel_id, strategy="activity", value="Pick Item")
    assert result["new_ocel_id"] != ocel_id
    assert result["filter"] == "filter_ocel_cc(activity)"
    assert result["num_events_after"] > 0


def test_filter_ocel_cc_object(ocel_id: str) -> None:
    result = filter_ocel_cc(ocel_id, strategy="object", value="o1")
    # CC of o1 includes the order, its items, and its delivery
    assert result["num_events_after"] > 0
    assert result["num_objects_after"] > 0


def test_filter_ocel_cc_otype_keep(ocel_id: str) -> None:
    result = filter_ocel_cc(ocel_id, strategy="otype", value="order", retain=True)
    assert result["new_ocel_id"] != ocel_id
    assert result["num_events_after"] > 0


def test_filter_ocel_cc_length_wide_range_keeps_all(ocel_id: str) -> None:
    # CC length = objects in a connected component. A wide range keeps all CCs.
    result = filter_ocel_cc(ocel_id, strategy="length", value=[1, 100])
    assert result["num_events_after"] == 10


def test_filter_ocel_cc_length_rejects_bad_shape(ocel_id: str) -> None:
    with pytest.raises(ValueError):
        filter_ocel_cc(ocel_id, strategy="length", value="not-a-list")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        filter_ocel_cc(ocel_id, strategy="length", value=[1, 2, 3])  # wrong length
    with pytest.raises(ValueError):
        filter_ocel_cc(ocel_id, strategy="length", value=[5, 2])  # min > max


def test_filter_ocel_cc_activity_rejects_non_string_value(ocel_id: str) -> None:
    with pytest.raises(ValueError):
        filter_ocel_cc(ocel_id, strategy="activity", value=["Ship"])  # type: ignore[arg-type]


def test_filter_ocel_cc_unknown_strategy(ocel_id: str) -> None:
    with pytest.raises(UnsupportedFormat):
        filter_ocel_cc(ocel_id, strategy="weirdo", value="x")  # type: ignore[arg-type]


# --- error paths shared across tools ---


def test_ocel_filter_tools_raise_on_missing_handle() -> None:
    with pytest.raises(HandleNotFound):
        filter_ocel_time_range("ocel-gone", start="2024-01-01", end="2024-01-02")
    with pytest.raises(HandleNotFound):
        filter_ocel_attribute("ocel-gone", attribute="ocel:activity", values=["Ship"])
    with pytest.raises(HandleNotFound):
        filter_ocel_object_types("ocel-gone", types=["order"])
    with pytest.raises(HandleNotFound):
        filter_ocel_cc("ocel-gone", strategy="activity", value="Ship")


def test_ocel_filter_tools_reject_wrong_kind() -> None:
    h = registry.put("log", object())
    with pytest.raises(InvalidKind):
        filter_ocel_time_range(h, start="2024-01-01", end="2024-01-02")
    with pytest.raises(InvalidKind):
        filter_ocel_attribute(h, attribute="x", values=["y"])
    with pytest.raises(InvalidKind):
        filter_ocel_object_types(h, types=["order"])
    with pytest.raises(InvalidKind):
        filter_ocel_cc(h, strategy="activity", value="Ship")


def test_filter_chain_preserves_original(ocel_id: str) -> None:
    """Filters are pure: each call mints a fresh ocel_id and never mutates the source."""
    r1 = filter_ocel_object_types(ocel_id, types=["order"], retain=True)
    r2 = filter_ocel_attribute(r1["new_ocel_id"], attribute="ocel:activity", values=["Place Order"])

    # All three handles distinct
    assert len({ocel_id, r1["new_ocel_id"], r2["new_ocel_id"]}) == 3
    # Original OCEL unchanged in registry
    kind, _ = registry.get(ocel_id)
    assert kind == "ocel"
    # r2's before counts equal r1's after counts (chain linearity)
    assert r2["num_events_before"] == r1["num_events_after"]
    assert r2["num_objects_before"] == r1["num_objects_after"]
