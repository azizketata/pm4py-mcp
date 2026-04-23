"""Shared pytest configuration for the four-layer testing pyramid."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure editable-install style imports work even if the project isn't
# installed in the current interpreter (useful for quick local pytest runs).
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(autouse=True)
def _isolate_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect the workspace to a per-test tmp directory.

    Every test gets its own clean workspace so parallel runs don't fight over
    filenames and no test pollutes the user's real ``~/.pm4py-mcp/workspace``.
    """
    ws = tmp_path / "pm4py-mcp-ws"
    monkeypatch.setenv("PM4PY_MCP_WORKSPACE", str(ws))
    return ws
