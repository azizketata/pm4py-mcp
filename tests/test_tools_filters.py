"""Slice 4 — filter tool unit tests."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound
from pm4py_mcp.server import registry
from pm4py_mcp.tools.filters import (
    filter_attribute_values,
    filter_case_performance,
    filter_case_size,
    filter_time_range,
    filter_variants,
)
from tests.fixtures import tiny_log


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log())


# --- filter_variants ---


def test_filter_variants_top_k_retains_most_common(log_id: str) -> None:
    """tiny_log has 2 variants: happy path x2 (cases 1-2, 8 events) + incomplete x1 (case 3, 3 events)."""
    result = filter_variants(log_id, top_k=1, retain=True)
    assert result["new_log_id"].startswith("log-")
    assert result["new_log_id"] != log_id
    assert result["filter"] == "filter_variants"
    assert result["num_cases_before"] == 3
    assert result["num_cases_after"] == 2  # keeps happy path x2
    assert result["num_events_after"] == 8


def test_filter_variants_explicit_list(log_id: str) -> None:
    result = filter_variants(
        log_id,
        variants=[["register", "triage", "treat"]],
        retain=True,
    )
    assert result["num_cases_after"] == 1  # only case 3 matches
    assert result["num_events_after"] == 3


def test_filter_variants_retain_false_inverts(log_id: str) -> None:
    result = filter_variants(log_id, top_k=1, retain=False)
    # Remove the most common → keep case 3 only
    assert result["num_cases_after"] == 1


def test_filter_variants_requires_exactly_one_selector(log_id: str) -> None:
    with pytest.raises(ValueError):
        filter_variants(log_id)  # neither
    with pytest.raises(ValueError):
        filter_variants(log_id, top_k=1, variants=[["a"]])  # both


def test_filter_variants_rejects_zero_top_k(log_id: str) -> None:
    with pytest.raises(ValueError):
        filter_variants(log_id, top_k=0)


# --- filter_time_range ---


def test_filter_time_range_window_includes_all(log_id: str) -> None:
    result = filter_time_range(
        log_id,
        start="2024-01-01T00:00:00",
        end="2024-01-02T00:00:00",
        mode="events",
    )
    assert result["num_events_after"] == 11  # all events


def test_filter_time_range_narrow_window(log_id: str) -> None:
    # 08:00-08:30 catches only case-1's register + triage
    result = filter_time_range(
        log_id,
        start="2024-01-01T08:00:00",
        end="2024-01-01T08:30:00",
        mode="events",
    )
    assert result["num_events_after"] < 11
    assert result["num_events_after"] >= 2


# --- filter_attribute_values ---


def test_filter_attribute_values_event_level_retain(log_id: str) -> None:
    # Keep only "treat" events → 3 events (one per case that has treat)
    result = filter_attribute_values(
        log_id,
        attribute="concept:name",
        values=["treat"],
        retain=True,
        level="event",
    )
    assert result["num_events_after"] == 3


def test_filter_attribute_values_event_level_drop(log_id: str) -> None:
    result = filter_attribute_values(
        log_id,
        attribute="concept:name",
        values=["treat"],
        retain=False,
        level="event",
    )
    assert result["num_events_after"] == 11 - 3


def test_filter_attribute_values_case_level(log_id: str) -> None:
    # Keep only cases that had a "discharge" event → cases 1, 2 (8 events)
    result = filter_attribute_values(
        log_id,
        attribute="concept:name",
        values=["discharge"],
        retain=True,
        level="case",
    )
    assert result["num_cases_after"] == 2
    assert result["num_events_after"] == 8


def test_filter_attribute_values_rejects_empty_values(log_id: str) -> None:
    with pytest.raises(ValueError):
        filter_attribute_values(
            log_id,
            attribute="concept:name",
            values=[],
        )


# --- filter_case_size ---


def test_filter_case_size_keeps_4event_cases(log_id: str) -> None:
    result = filter_case_size(log_id, min_size=4, max_size=4)
    assert result["num_cases_after"] == 2
    assert result["num_events_after"] == 8


def test_filter_case_size_keeps_3event_cases(log_id: str) -> None:
    result = filter_case_size(log_id, min_size=3, max_size=3)
    assert result["num_cases_after"] == 1
    assert result["num_events_after"] == 3


def test_filter_case_size_rejects_invalid_bounds(log_id: str) -> None:
    with pytest.raises(ValueError):
        filter_case_size(log_id, min_size=5, max_size=3)
    with pytest.raises(ValueError):
        filter_case_size(log_id, min_size=-1, max_size=5)


# --- filter_case_performance ---


def test_filter_case_performance_fast_cases(log_id: str) -> None:
    # Case 3: treat at 11:00 - register at 10:00 = 1h = 3600s (shortest)
    # Case 1: 3.5h = 12600s
    # Case 2: 4h = 14400s
    result = filter_case_performance(log_id, min_seconds=0, max_seconds=7200)
    assert result["num_cases_after"] == 1


def test_filter_case_performance_rejects_invalid_bounds(log_id: str) -> None:
    with pytest.raises(ValueError):
        filter_case_performance(log_id, min_seconds=-1, max_seconds=100)
    with pytest.raises(ValueError):
        filter_case_performance(log_id, min_seconds=200, max_seconds=100)


# --- error paths ---


def test_filter_tools_raise_on_missing_handle() -> None:
    with pytest.raises(HandleNotFound):
        filter_case_size("log-gone", min_size=1, max_size=10)
    with pytest.raises(HandleNotFound):
        filter_case_performance("log-gone", min_seconds=0, max_seconds=10)
    with pytest.raises(HandleNotFound):
        filter_time_range("log-gone", start="2024-01-01", end="2024-01-02")


def test_filter_chain_creates_distinct_handles(log_id: str) -> None:
    """Filtering is pure: each call mints a fresh log_id."""
    r1 = filter_case_size(log_id, min_size=3, max_size=4)
    r2 = filter_case_size(r1["new_log_id"], min_size=4, max_size=4)
    # All three handles distinct
    assert len({log_id, r1["new_log_id"], r2["new_log_id"]}) == 3
    # Original log unmodified in registry
    kind, _ = registry.get(log_id)
    assert kind == "log"
