"""Phase 3 Slice 4 — end-to-end stdio subprocess test for the agentic layer.

Walks through the canonical Phase 3 chain over real stdio JSON-RPC:
    load_event_log
    → describe_log
    → abstract_log_features / abstract_variants / abstract_dfg
    → discover_petri_net
    → abstract_petri_net
    → set_domain_context + get_domain_context
    → render_report (with the petri_id handle's structural abstraction as prose)

Also asserts the overall tool + prompt surface is correct for 0.3.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = [pytest.mark.asyncio, pytest.mark.subprocess]

EXAMPLE_XES = Path(__file__).resolve().parent.parent / "examples" / "running-example.xes"


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=["-m", "pm4py_mcp"])


def _json(content) -> dict:  # type: ignore[no-untyped-def]
    text = getattr(content[0], "text", "")
    return json.loads(text)


@pytest.mark.skipif(not EXAMPLE_XES.is_file(), reason="examples/running-example.xes missing")
async def test_phase3_agentic_workflow_over_stdio(tmp_path: Path) -> None:
    """abstract + context + render_report, end-to-end through stdio."""
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "pm4py-mcp"

            # Tool surface: 24 Phase 1 + 12 Phase 2 OCEL + 9 Phase 3 abstractions
            # + 2 context + 1 render_report + 1 sample_case_ids (0.3.2) = 49
            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            assert len(tools.tools) == 49

            for expected in (
                "abstract_log_features",
                "abstract_log_attributes",
                "abstract_variants",
                "abstract_dfg",
                "abstract_case",
                "abstract_stream",
                "abstract_petri_net",
                "abstract_ocel",
                "abstract_ocdfg",
                "set_domain_context",
                "get_domain_context",
                "render_report",
            ):
                assert expected in tool_names, f"{expected} missing from tools/list"

            # Prompt surface: 6 curated workflows
            prompts = await session.list_prompts()
            prompt_names = {p.name for p in prompts.prompts}
            assert len(prompts.prompts) == 6
            assert prompt_names == {
                "bottleneck_analysis",
                "conformance_workflow",
                "executive_summary",
                "new_log_onboarding",
                "ocel_flattening_workflow",
                "variant_exploration",
            }

            # 1. Load the bundled running-example.
            r = await session.call_tool("load_event_log", {"path": str(EXAMPLE_XES)})
            assert not r.isError
            load = _json(r.content)
            log_id = load["log_id"]
            assert load["num_cases"] == 8

            # 2. abstract_variants → the narrative Claude reasons over
            r = await session.call_tool("abstract_variants", {"log_id": log_id})
            assert not r.isError
            variants_desc = _json(r.content)
            assert "content" in variants_desc
            assert variants_desc["tool"] == "abstract_variants"
            assert variants_desc["approx_tokens"] >= 1

            # 3. abstract_dfg for the narrative
            r = await session.call_tool("abstract_dfg", {"log_id": log_id})
            assert not r.isError
            dfg_desc = _json(r.content)
            assert dfg_desc["tool"] == "abstract_dfg"

            # 4. discover_petri_net → abstract_petri_net
            r = await session.call_tool("discover_petri_net", {"log_id": log_id})
            assert not r.isError
            petri = _json(r.content)
            petri_id = petri["petri_id"]

            r = await session.call_tool("abstract_petri_net", {"petri_id": petri_id})
            assert not r.isError
            petri_desc = _json(r.content)
            assert petri_desc["tool"] == "abstract_petri_net"
            assert len(petri_desc["content"]) > 0

            # 5. Domain context roundtrip
            r = await session.call_tool(
                "set_domain_context",
                {"text_or_path": "SOP: running-example is a compliance demo process."},
            )
            assert not r.isError
            set_ctx = _json(r.content)
            assert set_ctx["name"] == "default"
            assert set_ctx["stored_context_count"] == 1

            r = await session.call_tool("get_domain_context", {})
            assert not r.isError
            got_ctx = _json(r.content)
            assert "compliance demo" in got_ctx["content"]

            # 6. render_report consolidating the narrative
            findings = (
                "## Variants\n\n"
                f"{variants_desc['content']}\n\n"
                "## DFG\n\n"
                f"{dfg_desc['content']}\n\n"
                "## Model\n\n"
                f"{petri_desc['content']}"
            )
            report_path = tmp_path / "phase3-e2e-report.md"
            r = await session.call_tool(
                "render_report",
                {
                    "title": "Phase 3 E2E Report",
                    "findings": findings,
                    "output_path": str(report_path),
                },
            )
            assert not r.isError
            report = _json(r.content)
            assert Path(report["path"]) == report_path.resolve()
            assert report["size_bytes"] > 0
            assert report["num_artifacts"] == 0

            body = report_path.read_text(encoding="utf-8")
            assert body.startswith("# Phase 3 E2E Report")
            assert "## Variants" in body
            assert "## Model" in body


@pytest.mark.skipif(not EXAMPLE_XES.is_file(), reason="examples/running-example.xes missing")
async def test_prompts_get_over_stdio() -> None:
    """Ensure prompts/get works over the wire (not just in-process)."""
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            got = await session.get_prompt("new_log_onboarding", {"log_path": str(EXAMPLE_XES)})
            assert len(got.messages) == 1
            msg = got.messages[0]
            text = getattr(msg.content, "text", "")
            assert "load_event_log" in text
            assert "abstract_variants" in text
