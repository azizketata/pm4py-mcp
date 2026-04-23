"""Layer 2: in-process ClientSession tests.

Exercises the full MCP protocol (initialize -> list_tools -> call_tool)
over in-memory streams, with no subprocess. Catches tool-registration,
schema, and handler-wiring bugs at a few-millisecond feedback latency.
"""

from __future__ import annotations

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from pm4py_mcp.server import mcp

pytestmark = [pytest.mark.asyncio, pytest.mark.in_process]


async def test_list_tools_includes_ping() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        tools = await client.list_tools()
        names = [t.name for t in tools.tools]
        assert "ping" in names


async def test_call_ping_returns_pong() -> None:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("ping", {})
        assert not result.isError
        assert result.content, "ping must return at least one content block"
        text_block = result.content[0]
        # FastMCP wraps string returns in a TextContent block
        text = getattr(text_block, "text", "")
        assert "pong" in text
