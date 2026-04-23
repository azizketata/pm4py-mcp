"""Slice 5 — end-to-end workflow test over stdio subprocess.

The final layer of the testing pyramid: drives the server exactly as
Claude Desktop would — a fresh subprocess, stdio transport, real
JSON-RPC messages — and walks through the full Phase 1 tool chain with
handle propagation between calls.

Unlike the per-category MCP tests in ``test_tools_mcp.py`` (which use
in-memory streams), this exercises:

- Subprocess spawning and stdio framing
- Server startup under PATH/CWD constraints
- Round-trip JSON serialization of every response
- Handle lifecycles across separate tool calls

If this test fails on a platform where in-process tests pass, the bug
is almost always in PATH, CWD, encoding, or Graphviz — the classic MCP
failure modes Phase 0 was built to defend against.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = [pytest.mark.asyncio, pytest.mark.subprocess]

EXAMPLE_XES = Path(__file__).resolve().parent.parent / "examples" / "running-example.xes"
_has_graphviz = shutil.which("dot") is not None


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=["-m", "pm4py_mcp"])


def _json(content) -> dict:  # type: ignore[no-untyped-def]
    """Extract the JSON payload from the first TextContent block."""
    text = getattr(content[0], "text", "")
    return json.loads(text)


@pytest.mark.skipif(not EXAMPLE_XES.is_file(), reason="examples/running-example.xes missing")
async def test_full_phase1_workflow_over_stdio() -> None:
    """load → describe → discover → conformance → filter → export, all over stdio."""
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "pm4py-mcp"

            # Phase 1 (24) + Phase 2 Slice 1 OCEL I/O (4) + Slice 2 OCEL discovery/viz (4)
            # = 32 tools total as of 0.2.0 Slice 2.
            tools = await session.list_tools()
            assert len(tools.tools) == 32

            # 1. Load
            r = await session.call_tool("load_event_log", {"path": str(EXAMPLE_XES)})
            assert not r.isError
            load = _json(r.content)
            log_id = load["log_id"]
            assert load["num_cases"] == 8
            assert load["num_events"] == 32

            # 2. Describe
            r = await session.call_tool("describe_log", {"log_id": log_id})
            assert _json(r.content) == load

            # 3. Variants stats
            r = await session.call_tool("get_variants", {"log_id": log_id})
            assert _json(r.content)["total_variants"] == 2

            # 4. Discover Petri net
            r = await session.call_tool(
                "discover_petri_net",
                {"log_id": log_id, "algorithm": "inductive", "noise_threshold": 0.2},
            )
            petri_id = _json(r.content)["petri_id"]

            # 5. Token-replay conformance — self-model should be perfectly fit
            r = await session.call_tool(
                "conformance_token_replay",
                {"log_id": log_id, "petri_id": petri_id},
            )
            replay = _json(r.content)
            assert replay["num_cases"] == 8
            assert replay["mean_trace_fitness"] >= 0.95

            # 6. Filter to the consult variant — should leave 2 cases
            r = await session.call_tool(
                "filter_attribute_values",
                {
                    "log_id": log_id,
                    "attribute": "concept:name",
                    "values": ["consult"],
                    "level": "case",
                },
            )
            filtered = _json(r.content)
            assert filtered["num_cases_after"] == 2
            assert filtered["new_log_id"] != log_id

            # 7. Export the filtered log as CSV
            r = await session.call_tool(
                "export_log",
                {
                    "log_id": filtered["new_log_id"],
                    "format": "csv",
                    "path": "workflow-stdio-export",
                },
            )
            export = _json(r.content)
            assert Path(export["path"]).is_file()
            assert export["size_bytes"] > 0


@pytest.mark.skipif(
    not EXAMPLE_XES.is_file() or not _has_graphviz,
    reason="needs both examples/running-example.xes and Graphviz `dot` on PATH",
)
async def test_visualization_over_stdio_returns_inline_image() -> None:
    """Verify the mixed text+image content channel survives stdio serialization."""
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            r = await session.call_tool("load_event_log", {"path": str(EXAMPLE_XES)})
            log_id = _json(r.content)["log_id"]

            r = await session.call_tool("discover_petri_net", {"log_id": log_id})
            petri_id = _json(r.content)["petri_id"]

            r = await session.call_tool("visualize_petri_net", {"petri_id": petri_id})
            assert not r.isError

            # First block is text caption with PNG/SVG paths, second is inline image.
            assert len(r.content) == 2
            text_block = r.content[0]
            image_block = r.content[1]

            assert getattr(text_block, "type", None) == "text"
            caption = getattr(text_block, "text", "")
            assert "PNG:" in caption
            assert "SVG:" in caption

            assert getattr(image_block, "type", None) == "image"
            assert getattr(image_block, "mimeType", None) == "image/png"
            # Base64-encoded data should be non-empty.
            assert len(getattr(image_block, "data", "")) > 100

            # Both files actually exist on disk.
            png_line = next(line for line in caption.splitlines() if line.startswith("PNG:"))
            svg_line = next(line for line in caption.splitlines() if line.startswith("SVG:"))
            png = Path(png_line.removeprefix("PNG: ").strip())
            svg = Path(svg_line.removeprefix("SVG: ").strip())
            assert png.is_file() and png.stat().st_size > 0
            assert svg.is_file() and svg.stat().st_size > 0
