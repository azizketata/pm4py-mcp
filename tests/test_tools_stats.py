"""Slice 2 — stats tool unit tests."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound
from pm4py_mcp.server import registry
from pm4py_mcp.tools.stats import (
    get_case_durations,
    get_cycle_time,
    get_start_end_activities,
    get_variants,
)
from tests.fixtures import tiny_log


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


def test_get_variants_reports_two_variants() -> None:
    log_id = registry.put("log", tiny_log())
    result = get_variants(log_id)

    assert result["log_id"] == log_id
    assert result["total_variants"] == 2
    traces = [tuple(v["trace"]) for v in result["variants"]]
    assert ("register", "triage", "treat", "discharge") in traces
    assert ("register", "triage", "treat") in traces
    # top variant (the 4-step happy path) has count 2
    assert result["variants"][0]["count"] == 2


def test_get_variants_respects_top_k() -> None:
    log_id = registry.put("log", tiny_log())
    result = get_variants(log_id, top_k=1)
    assert result["returned"] == 1
    assert result["total_variants"] == 2


def test_get_start_end_activities() -> None:
    log_id = registry.put("log", tiny_log())
    result = get_start_end_activities(log_id)

    # All cases start with "register"
    assert result["start"] == {"register": 3}
    # Two cases end with "discharge", one with "treat"
    assert result["end"]["discharge"] == 2
    assert result["end"]["treat"] == 1


def test_get_case_durations_returns_summary_stats() -> None:
    log_id = registry.put("log", tiny_log())
    result = get_case_durations(log_id)

    assert result["count"] == 3
    assert result["min"] <= result["median"] <= result["max"]
    assert result["mean"] > 0
    # All reported percentiles present
    assert set(result["percentiles"].keys()) == {"p50", "p75", "p90", "p95", "p99"}
    for v in result["percentiles"].values():
        assert result["min"] <= v <= result["max"]


def test_get_cycle_time_returns_float() -> None:
    log_id = registry.put("log", tiny_log())
    result = get_cycle_time(log_id)
    assert result["log_id"] == log_id
    assert isinstance(result["cycle_time_seconds"], float)
    assert result["cycle_time_seconds"] >= 0.0


def test_stats_tools_raise_on_missing_handle() -> None:
    for fn in (get_variants, get_start_end_activities, get_case_durations, get_cycle_time):
        with pytest.raises(HandleNotFound):
            fn("log-nope")
