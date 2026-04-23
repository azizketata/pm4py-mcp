"""Layer 3: stdio subprocess tests.

The anchor of Phase 0. Spawns the server as a real subprocess over stdio
and speaks MCP to it — catching the failure modes that only appear in
production: PATH issues, CWD assumptions, encoding mismatches, startup
ordering, and Windows console quirks.

Do not skip this layer on Windows. Claude Desktop ships on Windows and
this is the closest approximation we have to that environment.
"""

from __future__ import annotations

import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = [pytest.mark.asyncio, pytest.mark.subprocess]


def _server_params() -> StdioServerParameters:
    # Use the current interpreter + `-m pm4py_mcp` so the test is hermetic
    # and doesn't depend on the console script being on PATH.
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "pm4py_mcp"],
    )


async def test_initialize_handshake() -> None:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "pm4py-mcp"


async def test_ping_roundtrip() -> None:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("ping", {})
            assert not result.isError
            assert result.content
            text = getattr(result.content[0], "text", "")
            assert "pong" in text
