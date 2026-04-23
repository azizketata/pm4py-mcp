"""In-process MCP tests covering Phase 1 tool categories.

Walks each tool through the MCP protocol via an in-memory ClientSession —
exercising registration, schema validation, handler dispatch, and result
serialization that the direct-call unit tests don't touch. Grows per slice:
Slice 2 added io + stats; Slice 3 adds discovery + visualization.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from pm4py_mcp.server import mcp, registry
from tests.fixtures import tiny_log, tiny_log_xes

pytestmark = [pytest.mark.asyncio, pytest.mark.in_process]

_has_graphviz = shutil.which("dot") is not None


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
        # ping + I/O (4) + stats (4) + discovery (4) + visualization (4) = 17
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
            "discover_dfg",
            "discover_petri_net",
            "discover_process_tree",
            "discover_bpmn",
            "visualize_dfg",
            "visualize_petri_net",
            "visualize_process_tree",
            "visualize_bpmn",
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


async def test_discovery_chain_via_mcp() -> None:
    log_id = registry.put("log", tiny_log())
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        dfg = _unwrap((await client.call_tool("discover_dfg", {"log_id": log_id})).content)
        petri = _unwrap((await client.call_tool("discover_petri_net", {"log_id": log_id})).content)
        tree = _unwrap(
            (await client.call_tool("discover_process_tree", {"log_id": log_id})).content
        )
        bpmn = _unwrap((await client.call_tool("discover_bpmn", {"log_id": log_id})).content)

        assert dfg["dfg_id"].startswith("dfg-")
        assert petri["petri_id"].startswith("pn-")
        assert petri["algorithm"] == "inductive"
        assert tree["tree_id"].startswith("pt-")
        assert bpmn["bpmn_id"].startswith("bpmn-")


async def test_discover_petri_net_with_noise_threshold_via_mcp() -> None:
    log_id = registry.put("log", tiny_log())
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = _unwrap(
            (
                await client.call_tool(
                    "discover_petri_net",
                    {"log_id": log_id, "noise_threshold": 0.2},
                )
            ).content
        )
        assert result["noise_threshold"] == 0.2


async def test_visualization_without_graphviz_returns_tool_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_id = registry.put("log", tiny_log())
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        petri = _unwrap((await client.call_tool("discover_petri_net", {"log_id": log_id})).content)

        monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
        result = await client.call_tool("visualize_petri_net", {"petri_id": petri["petri_id"]})
        assert result.isError is True


@pytest.mark.skipif(not _has_graphviz, reason="Graphviz `dot` binary not installed")
async def test_visualize_petri_net_via_mcp_returns_caption_and_image() -> None:
    log_id = registry.put("log", tiny_log())
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        petri = _unwrap((await client.call_tool("discover_petri_net", {"log_id": log_id})).content)
        result = await client.call_tool("visualize_petri_net", {"petri_id": petri["petri_id"]})
        assert not result.isError
        # First block is the TextContent caption, second is ImageContent.
        assert len(result.content) == 2
        first = result.content[0]
        second = result.content[1]
        assert getattr(first, "type", None) == "text"
        assert "PNG:" in getattr(first, "text", "")
        assert getattr(second, "type", None) == "image"
        assert getattr(second, "mimeType", None) == "image/png"
