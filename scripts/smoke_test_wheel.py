"""Smoke-test the locally-built wheel end-to-end over stdio.

Simulates what `uvx --from pm4py-mcp==<version> pm4py-mcp` does after a real
TestPyPI release: install the wheel into a fresh environment, spawn the
`pm4py-mcp` entry point, and verify via the MCP protocol that the
artifact exposes the expected surface (48 tools + 6 prompts since 0.3.0).

The expected version string is read from `importlib.metadata` at runtime
so the script does not need to be edited per release.

Run via:

    uv run --isolated --no-project \
        --with dist/pm4py_mcp-<version>-py3-none-any.whl \
        --with "mcp>=1.20,<2" \
        python scripts/smoke_test_wheel.py
"""

from __future__ import annotations

import asyncio
import sys
from importlib.metadata import version

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOL_COUNT = 49
EXPECTED_PROMPT_COUNT = 6
EXPECTED_PROMPT_NAMES = {
    "bottleneck_analysis",
    "conformance_workflow",
    "executive_summary",
    "new_log_onboarding",
    "ocel_flattening_workflow",
    "variant_exploration",
}
EXPECTED_CORE_TOOLS = (
    "ping",
    "load_event_log",
    "load_ocel",
    "abstract_variants",
    "abstract_petri_net",
    "abstract_ocel",
    "set_domain_context",
    "get_domain_context",
    "render_report",
    "sample_case_ids",  # 0.3.2
)


async def main() -> int:
    expected_version = version("pm4py-mcp")
    expected_ping = f"pong pm4py-mcp {expected_version}"
    print(f"expecting: {expected_ping}")

    params = StdioServerParameters(command="pm4py-mcp", args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"serverInfo: {init.serverInfo.name} v{init.serverInfo.version}")

            tools = await session.list_tools()
            tool_names = sorted(t.name for t in tools.tools)
            print(f"tools/list: {len(tool_names)} tools")
            assert len(tool_names) == EXPECTED_TOOL_COUNT, (
                f"expected {EXPECTED_TOOL_COUNT} tools, got {len(tool_names)}"
            )
            for core in EXPECTED_CORE_TOOLS:
                assert core in tool_names, f"{core} missing from tools/list"

            prompts = await session.list_prompts()
            prompt_names = {p.name for p in prompts.prompts}
            print(f"prompts/list: {len(prompt_names)} prompts")
            assert prompt_names == EXPECTED_PROMPT_NAMES, (
                f"prompt surface mismatch: {prompt_names}"
            )

            ping = await session.call_tool("ping", {})
            ping_text = getattr(ping.content[0], "text", "")
            print(f"ping: {ping_text}")
            assert expected_ping in ping_text, f"version mismatch: {ping_text}"

            got = await session.get_prompt("new_log_onboarding", {"log_path": "demo.xes"})
            msg_text = getattr(got.messages[0].content, "text", "")
            assert "load_event_log" in msg_text
            assert "abstract_variants" in msg_text
            print("prompts/get new_log_onboarding: body contains expected tool names")

    print("\nSMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
