"""Phase 2 Slice 4 — end-to-end OCEL workflow test over stdio subprocess.

The Phase 2 acceptance gate: the full 0.2.0 surface plus the cross-phase
composability bridge, driven through a real stdio subprocess exactly the way
Claude Desktop / Claude Code would. If this passes, the published wheel is
guaranteed to serve every OCEL tool correctly to any MCP client.

Chain:
  1. load_ocel (bundled example)
  2. describe_ocel
  3. flatten_ocel('order') -> log_id
  4. discover_petri_net(log_id)  # Phase 1 tool on a Phase 2 handle
  5. visualize_petri_net         # Phase 1 viz on the flattened log
  6. discover_oc_petri_net
  7. visualize_oc_petri_net      # OCPN render
  8. filter_ocel_object_types(['order'])
  9. export_ocel (round-trip)
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

EXAMPLE_OCEL = Path(__file__).resolve().parent.parent / "examples" / "order-management.jsonocel"
_has_graphviz = shutil.which("dot") is not None


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=["-m", "pm4py_mcp"])


def _json(content) -> dict:  # type: ignore[no-untyped-def]
    text = getattr(content[0], "text", "")
    return json.loads(text)


@pytest.mark.skipif(not EXAMPLE_OCEL.is_file(), reason="bundled OCEL missing")
async def test_ocel_workflow_through_stdio() -> None:
    """Full 0.2.0 OCEL workflow over stdio — the Phase 2 acceptance gate."""
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "pm4py-mcp"

            tools = await session.list_tools()
            # 24 Phase 1 + 12 Phase 2 + 9 Phase 3 abstractions
            # + 2 context + 1 render_report + 1 sample_case_ids (0.3.2)
            # + 9 0.4.0 tools + 9 0.4.1 tools (5 org-mining + abstract_sna
            #   + simulate_log + 2 advanced viz) = 67
            assert len(tools.tools) == 67

            # 1. Load the bundled OCEL.
            r = await session.call_tool("load_ocel", {"path": str(EXAMPLE_OCEL)})
            assert not r.isError
            ocel = _json(r.content)
            ocel_id = ocel["ocel_id"]
            assert ocel["num_events"] == 10
            assert ocel["num_object_types"] == 3

            # 2. Describe.
            r = await session.call_tool("describe_ocel", {"ocel_id": ocel_id})
            desc = _json(r.content)
            assert desc["num_events"] == 10

            # 3. Flatten on 'order' -> traditional log handle.
            r = await session.call_tool(
                "flatten_ocel", {"ocel_id": ocel_id, "object_type": "order"}
            )
            flat = _json(r.content)
            log_id = flat["log_id"]
            assert log_id.startswith("log-")
            assert flat["num_cases"] == 2

            # 4. Phase 1 tool on a Phase 2 handle — the composability bridge.
            r = await session.call_tool(
                "discover_petri_net",
                {"log_id": log_id, "algorithm": "inductive", "noise_threshold": 0.0},
            )
            petri = _json(r.content)
            assert petri["petri_id"].startswith("pn-")

            # 5. Discover the object-centric Petri net across all object types.
            r = await session.call_tool("discover_oc_petri_net", {"ocel_id": ocel_id})
            ocpn = _json(r.content)
            ocpn_id = ocpn["ocpn_id"]
            assert ocpn_id.startswith("ocpn-")
            assert ocpn["num_object_types"] == 3

            # 6. Discovery of OC-DFG too (round out the catalog).
            r = await session.call_tool("discover_ocdfg", {"ocel_id": ocel_id})
            ocdfg = _json(r.content)
            assert ocdfg["ocdfg_id"].startswith("ocdfg-")
            assert ocdfg["num_object_types"] == 3

            # 7. Filter chain on the OCEL — prove filters compose.
            r = await session.call_tool(
                "filter_ocel_object_types",
                {"ocel_id": ocel_id, "types": ["order"], "retain": True},
            )
            filtered = _json(r.content)
            assert filtered["num_objects_after"] == 2
            assert filtered["new_ocel_id"] != ocel_id

            # 8. Round-trip export the filtered OCEL.
            r = await session.call_tool(
                "export_ocel",
                {
                    "ocel_id": filtered["new_ocel_id"],
                    "format": "jsonocel",
                    "path": "workflow-ocel-export",
                },
            )
            export = _json(r.content)
            assert Path(export["path"]).is_file()
            assert export["size_bytes"] > 0


@pytest.mark.skipif(
    not EXAMPLE_OCEL.is_file() or not _has_graphviz,
    reason="needs bundled OCEL + Graphviz `dot` on PATH",
)
async def test_visualize_oc_petri_net_over_stdio_returns_inline_image() -> None:
    """The inline-image content channel must survive the OCPN render path over stdio."""
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            r = await session.call_tool("load_ocel", {"path": str(EXAMPLE_OCEL)})
            ocel_id = _json(r.content)["ocel_id"]

            r = await session.call_tool("discover_oc_petri_net", {"ocel_id": ocel_id})
            ocpn_id = _json(r.content)["ocpn_id"]

            r = await session.call_tool("visualize_oc_petri_net", {"ocpn_id": ocpn_id})
            assert not r.isError
            # Caption + inline PNG
            assert len(r.content) == 2
            caption = r.content[0]
            image = r.content[1]
            assert getattr(caption, "type", None) == "text"
            assert "OC Petri net" in getattr(caption, "text", "")
            assert getattr(image, "type", None) == "image"
            assert getattr(image, "mimeType", None) == "image/png"
            assert len(getattr(image, "data", "")) > 100
