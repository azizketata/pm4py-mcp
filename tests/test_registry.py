"""Slice 1 — LogRegistry unit tests."""

from __future__ import annotations

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind
from pm4py_mcp.registry import LogRegistry


class _FakeClockRegistry(LogRegistry):
    """Registry subclass with a monotonically-advancing fake clock.

    Using a fake clock instead of ``time.sleep`` keeps TTL tests deterministic
    and instant. ``advance`` is the only knob the test harness needs.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._t: float = 0.0

    def _now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def test_put_get_roundtrip() -> None:
    r = LogRegistry()
    h = r.put("log", {"df": "payload"})
    kind, payload = r.get(h)
    assert kind == "log"
    assert payload == {"df": "payload"}


def test_handle_prefix_matches_kind() -> None:
    r = LogRegistry()
    assert r.put("log", None).startswith("log-")
    assert r.put("petri_net", None).startswith("pn-")
    assert r.put("process_tree", None).startswith("pt-")
    assert r.put("bpmn", None).startswith("bpmn-")
    assert r.put("dfg", None).startswith("dfg-")


def test_handle_uniqueness() -> None:
    r = LogRegistry(capacity=10_000)
    handles = {r.put("log", i) for i in range(1_000)}
    assert len(handles) == 1_000


def test_lru_eviction_beyond_capacity() -> None:
    r = LogRegistry(capacity=3)
    h1 = r.put("log", 1)
    h2 = r.put("log", 2)
    h3 = r.put("log", 3)
    h4 = r.put("log", 4)  # should evict h1
    assert h1 not in r
    assert all(h in r for h in (h2, h3, h4))


def test_get_touches_handle_as_most_recent() -> None:
    r = LogRegistry(capacity=3)
    h1 = r.put("log", 1)
    h2 = r.put("log", 2)
    r.put("log", 3)
    # Touch h1 so it becomes most-recent.
    r.get(h1)
    # Now h2 should be the LRU victim on overflow.
    r.put("log", 4)
    assert h2 not in r
    assert h1 in r


def test_ttl_eviction_on_get() -> None:
    r = _FakeClockRegistry(ttl_seconds=10.0)
    h = r.put("log", "payload")
    r.advance(11.0)
    with pytest.raises(HandleNotFound):
        r.get(h)


def test_ttl_eviction_on_put() -> None:
    r = _FakeClockRegistry(ttl_seconds=10.0)
    h_old = r.put("log", "old")
    r.advance(11.0)
    r.put("log", "fresh")
    assert h_old not in r
    assert len(r) == 1


def test_missing_handle_raises_handle_not_found() -> None:
    r = LogRegistry()
    with pytest.raises(HandleNotFound):
        r.get("log-doesnotexist")


def test_expected_kind_mismatch_raises() -> None:
    r = LogRegistry()
    h = r.put("log", "payload")
    with pytest.raises(InvalidKind):
        r.get(h, expected_kind="petri_net")


def test_expected_kind_match_passes() -> None:
    r = LogRegistry()
    h = r.put("petri_net", "net_payload")
    kind, payload = r.get(h, expected_kind="petri_net")
    assert kind == "petri_net"
    assert payload == "net_payload"


def test_put_rejects_unknown_kind() -> None:
    r = LogRegistry()
    with pytest.raises(InvalidKind):
        r.put("not_a_kind", None)  # type: ignore[arg-type]


def test_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        LogRegistry(capacity=0)


def test_rejects_invalid_ttl() -> None:
    with pytest.raises(ValueError):
        LogRegistry(ttl_seconds=0)


def test_contains_rejects_non_string() -> None:
    r = LogRegistry()
    assert (42 in r) is False


def test_clear_empties_registry() -> None:
    r = LogRegistry()
    r.put("log", 1)
    r.put("log", 2)
    r.clear()
    assert len(r) == 0
