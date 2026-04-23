"""Slice 4 — conformance tool unit tests."""

from __future__ import annotations

from typing import Any

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind
from pm4py_mcp.server import registry
from pm4py_mcp.tools.conformance import (
    conformance_alignments,
    conformance_token_replay,
)
from pm4py_mcp.tools.discovery import discover_petri_net
from tests.fixtures import tiny_log


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_and_petri() -> tuple[str, str]:
    log_id = registry.put("log", tiny_log())
    petri_id = discover_petri_net(log_id, algorithm="inductive")["petri_id"]
    return log_id, petri_id


# --- token-based replay ---


def test_token_replay_self_model_is_fit(log_and_petri: tuple[str, str]) -> None:
    """A Petri net discovered from the same log should replay all traces as fit."""
    log_id, petri_id = log_and_petri
    result = conformance_token_replay(log_id, petri_id)

    assert result["log_id"] == log_id
    assert result["petri_id"] == petri_id
    assert result["algorithm"] == "token_replay"
    assert result["num_cases"] == 3
    assert result["num_fit_cases"] == 3
    assert result["mean_trace_fitness"] >= 0.95  # allow tiny numerical slack


def test_token_replay_rejects_wrong_log_kind(log_and_petri: tuple[str, str]) -> None:
    _, petri_id = log_and_petri
    with pytest.raises(InvalidKind):
        conformance_token_replay(petri_id, petri_id)  # first arg should be log


def test_token_replay_rejects_wrong_model_kind(log_and_petri: tuple[str, str]) -> None:
    log_id, _ = log_and_petri
    with pytest.raises(InvalidKind):
        conformance_token_replay(log_id, log_id)  # second arg should be petri


def test_token_replay_missing_handles() -> None:
    with pytest.raises(HandleNotFound):
        conformance_token_replay("log-gone", "pn-gone")


# --- alignments ---


async def test_alignments_self_model_is_fit(log_and_petri: tuple[str, str]) -> None:
    log_id, petri_id = log_and_petri
    result = await conformance_alignments(log_id, petri_id)

    assert result["log_id"] == log_id
    assert result["petri_id"] == petri_id
    assert result["algorithm"] == "alignments"
    assert result["num_cases"] == 3
    assert result["num_fit_cases"] == 3
    assert result["mean_trace_fitness"] == pytest.approx(1.0, abs=1e-6)


class _FakeCtx:
    """Minimal stand-in for ``mcp.server.fastmcp.Context`` in unit tests."""

    def __init__(self) -> None:
        self.progress_calls: list[tuple[float, float | None, str | None]] = []

    async def report_progress(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        self.progress_calls.append((progress, total, message))


async def test_alignments_emits_progress(log_and_petri: tuple[str, str]) -> None:
    log_id, petri_id = log_and_petri
    ctx = _FakeCtx()
    await conformance_alignments(log_id, petri_id, ctx=ctx)  # type: ignore[arg-type]
    # Start + end
    assert len(ctx.progress_calls) == 2
    start_progress, start_total, _ = ctx.progress_calls[0]
    end_progress, end_total, _ = ctx.progress_calls[1]
    assert start_progress == 0.0
    assert end_progress == end_total == 3.0
    assert start_total == 3.0


async def test_alignments_without_ctx_runs_fine(log_and_petri: tuple[str, str]) -> None:
    """Tool must work when invoked by a client that doesn't inject Context."""
    log_id, petri_id = log_and_petri
    result = await conformance_alignments(log_id, petri_id, ctx=None)
    assert result["num_cases"] == 3


async def test_alignments_rejects_wrong_kinds(log_and_petri: tuple[str, str]) -> None:
    log_id, petri_id = log_and_petri
    with pytest.raises(InvalidKind):
        await conformance_alignments(petri_id, petri_id)
    with pytest.raises(InvalidKind):
        await conformance_alignments(log_id, log_id)


def _assert_conformance_shape(r: dict[str, Any]) -> None:
    """Both tools must return the same key set."""
    expected = {
        "log_id",
        "petri_id",
        "algorithm",
        "num_cases",
        "num_fit_cases",
        "mean_trace_fitness",
    }
    assert set(r.keys()) == expected


async def test_conformance_result_shape_is_consistent(log_and_petri: tuple[str, str]) -> None:
    log_id, petri_id = log_and_petri
    replay = conformance_token_replay(log_id, petri_id)
    aligns = await conformance_alignments(log_id, petri_id)
    _assert_conformance_shape(replay)
    _assert_conformance_shape(aligns)
