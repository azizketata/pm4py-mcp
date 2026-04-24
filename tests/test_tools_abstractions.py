"""Phase 3 Slice 1 — log-level abstraction tool unit tests."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind, UnsupportedFormat
from pm4py_mcp.server import registry
from pm4py_mcp.tools.abstractions import (
    abstract_case,
    abstract_dfg,
    abstract_log_attributes,
    abstract_log_features,
    abstract_ocdfg,
    abstract_ocel,
    abstract_petri_net,
    abstract_stream,
    abstract_variants,
)
from tests.fixtures import tiny_log, tiny_ocel, tiny_petri_net


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log())


# --- shared shape expectations ---


_EXPECTED_KEYS = {"content", "approx_tokens", "truncated", "source_handle", "tool"}


def _assert_abstraction_shape(result: dict, tool_name: str, source_handle: str) -> None:
    assert set(result.keys()) == _EXPECTED_KEYS
    assert isinstance(result["content"], str)
    assert len(result["content"]) > 0
    assert isinstance(result["approx_tokens"], int)
    assert result["approx_tokens"] >= 1
    assert isinstance(result["truncated"], bool)
    assert result["source_handle"] == source_handle
    assert result["tool"] == tool_name


# --- abstract_log_features ---


def test_abstract_log_features_happy_path(log_id: str) -> None:
    result = abstract_log_features(log_id)
    _assert_abstraction_shape(result, "abstract_log_features", log_id)
    # Content should mention at least one of tiny_log's activities
    content_lower = result["content"].lower()
    assert any(a in content_lower for a in ("register", "triage", "treat", "discharge"))


def test_abstract_log_features_truncation_flag(log_id: str) -> None:
    # Flag should trigger whenever content meets or exceeds max_len — pm4py
    # doesn't always enforce the cap exactly (log_to_fea_descr emits whole
    # feature lines), so we assert the flag semantics, not the content size.
    result = abstract_log_features(log_id, max_len=50)
    assert result["truncated"] is True
    assert len(result["content"]) >= 50


# --- abstract_log_attributes ---


def test_abstract_log_attributes_happy_path(log_id: str) -> None:
    result = abstract_log_attributes(log_id)
    _assert_abstraction_shape(result, "abstract_log_attributes", log_id)


# --- abstract_variants ---


def test_abstract_variants_happy_path(log_id: str) -> None:
    result = abstract_variants(log_id)
    _assert_abstraction_shape(result, "abstract_variants", log_id)
    content_lower = result["content"].lower()
    # tiny_log has 2 variants; the happy-path one includes all four activities
    for activity in ("register", "triage", "treat", "discharge"):
        assert activity in content_lower


def test_abstract_variants_without_performance(log_id: str) -> None:
    result = abstract_variants(log_id, include_performance=False)
    _assert_abstraction_shape(result, "abstract_variants", log_id)


def test_abstract_variants_truncation(log_id: str) -> None:
    result = abstract_variants(log_id, max_len=80)
    assert result["truncated"] is True


# --- abstract_dfg ---


def test_abstract_dfg_happy_path(log_id: str) -> None:
    result = abstract_dfg(log_id)
    _assert_abstraction_shape(result, "abstract_dfg", log_id)
    content_lower = result["content"].lower()
    assert "register" in content_lower
    assert "triage" in content_lower


# --- abstract_case ---


def test_abstract_case_happy_path(log_id: str) -> None:
    result = abstract_case(log_id, case_id="case-1")
    _assert_abstraction_shape(result, "abstract_case", log_id)
    # case-1 is the happy path: register -> triage -> treat -> discharge
    content_lower = result["content"].lower()
    assert "register" in content_lower
    assert "discharge" in content_lower
    # abstract_case has no MAX_LEN knob, so truncated is always False
    assert result["truncated"] is False


def test_abstract_case_unknown_case_raises(log_id: str) -> None:
    with pytest.raises(UnsupportedFormat):
        abstract_case(log_id, case_id="case-999")


def test_abstract_case_without_event_attributes(log_id: str) -> None:
    result = abstract_case(log_id, case_id="case-1", include_event_attributes=False)
    _assert_abstraction_shape(result, "abstract_case", log_id)


def test_abstract_case_drops_nan_by_default(log_id: str) -> None:
    """0.3.2: tiny_log has no NaN attrs, so output shouldn't contain ' = nan'."""
    result = abstract_case(log_id, case_id="case-1")
    assert " = nan" not in result["content"]


def test_abstract_case_keeps_nan_when_opted_out(log_id: str) -> None:
    """Backward-compat path: drop_nan_attrs=False preserves pm4py's raw output.

    tiny_log has no NaN attributes, so the opt-out flag is functionally a
    no-op here; the assertion is simply that the call works and content is
    non-empty.
    """
    verbose = abstract_case(log_id, case_id="case-1", drop_nan_attrs=False)
    assert len(verbose["content"]) > 0


def test_abstract_case_nan_filter_preserves_non_nan_values() -> None:
    """On a log with NaN attrs, non-NaN values survive the filter unchanged."""
    import pandas as pd

    import pm4py as _pm4py

    # Craft a 2-event case where event 1 has CRP=59 but event 2 has CRP missing.
    df = pd.DataFrame(
        [
            ("c1", "register", "2024-01-01T08:00:00", 59.0),
            ("c1", "discharge", "2024-01-01T12:00:00", None),
        ],
        columns=["case_id", "activity", "timestamp", "CRP"],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    formatted = _pm4py.format_dataframe(
        df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )
    log_with_nans = registry.put("log", formatted)

    sparse = abstract_case(log_with_nans, "c1", drop_nan_attrs=True)["content"]
    verbose = abstract_case(log_with_nans, "c1", drop_nan_attrs=False)["content"]

    # CRP=59 present in both (not a NaN value)
    assert "CRP = 59" in sparse
    assert "CRP = 59" in verbose
    # NaN rendering gone from sparse, present in verbose
    assert " = nan" not in sparse
    assert " = nan" in verbose
    # Sparse is strictly shorter
    assert len(sparse) < len(verbose)


# --- abstract_stream ---


def test_abstract_stream_happy_path(log_id: str) -> None:
    result = abstract_stream(log_id)
    _assert_abstraction_shape(result, "abstract_stream", log_id)


def test_abstract_stream_truncation(log_id: str) -> None:
    result = abstract_stream(log_id, max_len=40)
    assert result["truncated"] is True


# --- error paths shared across tools ---


def test_all_abstractions_raise_on_missing_handle() -> None:
    for fn in (
        abstract_log_features,
        abstract_log_attributes,
        abstract_variants,
        abstract_dfg,
        abstract_stream,
    ):
        with pytest.raises(HandleNotFound):
            fn("log-gone")
    with pytest.raises(HandleNotFound):
        abstract_case("log-gone", case_id="case-1")


def test_all_abstractions_reject_wrong_kind() -> None:
    h = registry.put("petri_net", object())
    for fn in (
        abstract_log_features,
        abstract_log_attributes,
        abstract_variants,
        abstract_dfg,
        abstract_stream,
    ):
        with pytest.raises(InvalidKind):
            fn(h)
    with pytest.raises(InvalidKind):
        abstract_case(h, case_id="case-1")


# --- bridge: abstractions work on flattened OCEL logs ---


def test_abstract_variants_on_flattened_ocel() -> None:
    """Phase 2's flatten_ocel produces a log_id; Phase 3 abstractions should accept it."""
    from pm4py_mcp.tools.ocel_io import flatten_ocel

    ocel_id = registry.put("ocel", tiny_ocel())
    flat = flatten_ocel(ocel_id, object_type="order")
    result = abstract_variants(flat["log_id"])
    _assert_abstraction_shape(result, "abstract_variants", flat["log_id"])
    # The flattened order log has Place Order -> Pick Item -> Ship as the dominant variant
    content_lower = result["content"].lower()
    assert "place order" in content_lower


# --- Slice 2: abstract_petri_net ---


def test_abstract_petri_net_happy_path() -> None:
    net, im, fm = tiny_petri_net()
    petri_id = registry.put("petri_net", (net, im, fm))
    result = abstract_petri_net(petri_id)
    _assert_abstraction_shape(result, "abstract_petri_net", petri_id)
    # Net description should mention its structural elements
    content_lower = result["content"].lower()
    assert any(word in content_lower for word in ("place", "transition", "arc", "marking"))
    # net_to_descr has no MAX_LEN knob → truncated always False
    assert result["truncated"] is False


def test_abstract_petri_net_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        abstract_petri_net("pn-gone")


def test_abstract_petri_net_wrong_kind_raises() -> None:
    log_id = registry.put("log", tiny_log())
    with pytest.raises(InvalidKind):
        abstract_petri_net(log_id)


# --- Slice 2: abstract_ocel ---


def test_abstract_ocel_happy_path() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = abstract_ocel(ocel_id, object_type="order")
    _assert_abstraction_shape(result, "abstract_ocel", ocel_id)
    content_lower = result["content"].lower()
    assert "order" in content_lower


def test_abstract_ocel_unknown_object_type_raises() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    with pytest.raises(UnsupportedFormat):
        abstract_ocel(ocel_id, object_type="nonexistent_type")


def test_abstract_ocel_truncation() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = abstract_ocel(ocel_id, object_type="order", max_len=60)
    assert result["truncated"] is True


def test_abstract_ocel_wrong_kind_raises() -> None:
    log_id = registry.put("log", tiny_log())
    with pytest.raises(InvalidKind):
        abstract_ocel(log_id, object_type="order")


def test_abstract_ocel_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        abstract_ocel("ocel-gone", object_type="order")


# --- Slice 2: abstract_ocdfg ---


def test_abstract_ocdfg_happy_path() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = abstract_ocdfg(ocel_id)
    _assert_abstraction_shape(result, "abstract_ocdfg", ocel_id)
    content_lower = result["content"].lower()
    # OCDFG text should mention at least one object type
    assert any(ot in content_lower for ot in ("order", "item", "delivery"))


def test_abstract_ocdfg_without_performance() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = abstract_ocdfg(ocel_id, include_performance=False)
    _assert_abstraction_shape(result, "abstract_ocdfg", ocel_id)


def test_abstract_ocdfg_truncation() -> None:
    ocel_id = registry.put("ocel", tiny_ocel())
    result = abstract_ocdfg(ocel_id, max_len=80)
    assert result["truncated"] is True


def test_abstract_ocdfg_wrong_kind_raises() -> None:
    log_id = registry.put("log", tiny_log())
    with pytest.raises(InvalidKind):
        abstract_ocdfg(log_id)


def test_abstract_ocdfg_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        abstract_ocdfg("ocel-gone")
