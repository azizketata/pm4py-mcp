"""Slice 2 — in-process MCP tests for I/O + stats categories.

Walks each tool through the MCP protocol via an in-memory ClientSession —
exercising registration, schema validation, handler dispatch, and result
serialization that the direct-call unit tests don't touch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from pm4py_mcp.server import mcp, registry
from tests.fixtures import tiny_log, tiny_log_xes

pytestmark = [pytest.mark.asyncio, pytest.mark.in_process]


def _unwrap(result_content) -> dict:  # type: ignore[no-untyped-def]
    """Extract the first TextContent's JSON body as a dict."""
    text = getattr(result_content[0], "text", "")
    return json.loads(text)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


async def test_list_tools_contains_phase_1_surface() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        # ping + I/O (4) + stats (4) = 9
        assert "ping" in names
        for t in (
            "load_event_log",
            "describe_log",
            "export_log",
            "list_workspace",
            "get_variants",
            "get_start_end_activities",
            "get_case_durations",
            "get_cycle_time",
        ):
            assert t in names, f"{t} missing from tools/list"


async def test_load_and_describe_roundtrip_via_mcp(tmp_path: Path) -> None:
    xes_path = tiny_log_xes(tmp_path)
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        load_result = await client.call_tool("load_event_log", {"path": str(xes_path)})
        assert not load_result.isError
        load_payload = _unwrap(load_result.content)
        log_id = load_payload["log_id"]
        assert load_payload["num_cases"] == 3

        desc_result = await client.call_tool("describe_log", {"log_id": log_id})
        assert not desc_result.isError
        desc_payload = _unwrap(desc_result.content)
        assert desc_payload == load_payload


async def test_describe_log_bad_handle_returns_tool_error() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("describe_log", {"log_id": "log-nope"})
        assert result.isError is True


async def test_stats_tools_chain_via_mcp() -> None:
    log_id = registry.put("log", tiny_log())
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        variants = _unwrap((await client.call_tool("get_variants", {"log_id": log_id})).content)
        starts = _unwrap(
            (await client.call_tool("get_start_end_activities", {"log_id": log_id})).content
        )
        durations = _unwrap(
            (await client.call_tool("get_case_durations", {"log_id": log_id})).content
        )
        cycle = _unwrap((await client.call_tool("get_cycle_time", {"log_id": log_id})).content)

        assert variants["total_variants"] == 2
        assert starts["start"] == {"register": 3}
        assert durations["count"] == 3
        assert cycle["cycle_time_seconds"] >= 0.0


async def test_export_then_list_workspace_via_mcp() -> None:
    log_id = registry.put("log", tiny_log())
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        export = _unwrap(
            (
                await client.call_tool(
                    "export_log",
                    {"log_id": log_id, "format": "xes", "path": "mcp-export"},
                )
            ).content
        )
        assert Path(export["path"]).exists()

        listing = _unwrap((await client.call_tool("list_workspace", {})).content)
        assert listing["count"] >= 1
        assert any(e["name"].startswith("mcp-export") for e in listing["entries"])
