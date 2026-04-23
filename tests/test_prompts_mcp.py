"""Phase 3 Slice 3 — in-process MCP tests for the prompt library.

These go through ``prompts/list`` and ``prompts/get`` via the MCP wire format
rather than calling the decorated functions directly. That way we catch
registration bugs (typos in names, wrong argument inference, missing preamble
injection) that a direct-call test would miss.
"""

from __future__ import annotations

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from pm4py_mcp.server import mcp
from pm4py_mcp.tools.context import _clear_all_for_tests, set_domain_context

pytestmark = [pytest.mark.asyncio, pytest.mark.in_process]

EXPECTED_PROMPTS = {
    "bottleneck_analysis",
    "conformance_workflow",
    "executive_summary",
    "new_log_onboarding",
    "ocel_flattening_workflow",
    "variant_exploration",
}


@pytest.fixture(autouse=True)
def _clear_contexts() -> None:
    _clear_all_for_tests()


def _message_text(msg) -> str:  # type: ignore[no-untyped-def]
    return getattr(msg.content, "text", "")


async def test_prompts_list_returns_six_phase_3_prompts() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.list_prompts()
        names = {p.name for p in result.prompts}
        assert names == EXPECTED_PROMPTS
        # Every prompt has a human-readable title + description
        for p in result.prompts:
            assert p.title
            assert p.description


async def test_new_log_onboarding_body_mentions_core_tools() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt(
            "new_log_onboarding", {"log_path": "examples/benchmarks/sepsis.xes.gz"}
        )
        assert len(got.messages) == 1
        text = _message_text(got.messages[0])
        assert "sepsis.xes.gz" in text
        for tool in (
            "load_event_log",
            "describe_log",
            "abstract_log_features",
            "abstract_log_attributes",
            "abstract_variants",
        ):
            assert tool in text


async def test_conformance_workflow_body_mentions_replay_and_alignments() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt(
            "conformance_workflow",
            {"log_path": "tiny.xes", "noise_threshold": "0.1"},
        )
        text = _message_text(got.messages[0])
        for tool in (
            "load_event_log",
            "discover_petri_net",
            "conformance_token_replay",
            "conformance_alignments",
            "abstract_petri_net",
        ):
            assert tool in text
        assert "0.1" in text


async def test_bottleneck_analysis_body_mentions_duration_tools() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt("bottleneck_analysis", {"log_path": "bpi17.xes"})
        text = _message_text(got.messages[0])
        for tool in (
            "get_case_durations",
            "abstract_dfg",
            "abstract_variants",
            "discover_dfg",
            "visualize_dfg",
        ):
            assert tool in text


async def test_variant_exploration_body_uses_top_k() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt("variant_exploration", {"log_path": "tiny.xes", "k": "3"})
        text = _message_text(got.messages[0])
        assert "get_variants" in text
        assert "filter_variants" in text
        # the k value gets substituted into the body
        assert "top_k=3" in text or "top-3" in text


async def test_ocel_flattening_workflow_body_mentions_ocel_tools() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt("ocel_flattening_workflow", {"ocel_path": "order.jsonocel"})
        text = _message_text(got.messages[0])
        for tool in ("load_ocel", "describe_ocel", "flatten_ocel", "abstract_ocel"):
            assert tool in text


async def test_executive_summary_body_calls_render_report() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt(
            "executive_summary",
            {"log_id_or_path": "log-abc123", "title": "Q1 review"},
        )
        text = _message_text(got.messages[0])
        assert "render_report" in text
        assert "Q1 review" in text


async def test_prompt_prepends_domain_context_when_set() -> None:
    """If set_domain_context was called, the prompt body gets the domain preamble."""
    set_domain_context("Domain SOP: orders must clear fraud check before ship.")
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt("new_log_onboarding", {"log_path": "tiny.xes"})
        text = _message_text(got.messages[0])
        assert "Domain context" in text
        assert "fraud check before ship" in text


async def test_prompt_omits_preamble_when_no_context_set() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        got = await client.get_prompt("new_log_onboarding", {"log_path": "tiny.xes"})
        text = _message_text(got.messages[0])
        # Preamble header should be absent when nothing is registered
        assert "Domain context" not in text


async def test_prompts_get_missing_required_arg_is_error() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        # `bottleneck_analysis` requires `log_path`
        with pytest.raises(Exception):
            await client.get_prompt("bottleneck_analysis", {})


async def test_prompts_get_unknown_name_is_error() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        with pytest.raises(Exception):
            await client.get_prompt("nonexistent_prompt_name", {"log_path": "x"})
