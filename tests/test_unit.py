"""Layer 1: unit tests.

Catches logic bugs in tool bodies by calling the plain Python function
directly, bypassing the MCP protocol entirely. Fastest feedback loop;
these should always run first in CI.
"""

from __future__ import annotations

from pm4py_mcp import __version__
from pm4py_mcp.server import ping


def test_ping_returns_pong_and_version() -> None:
    result = ping()
    assert "pong" in result
    assert __version__ in result
    assert result.startswith("pong ")


def test_version_is_semver_shaped() -> None:
    parts = __version__.split(".")
    assert len(parts) >= 3
    for part in parts[:3]:
        # Allow pre-release suffixes like "1rc0" but require digit prefix
        assert part[0].isdigit(), f"version component {part!r} must start with a digit"
