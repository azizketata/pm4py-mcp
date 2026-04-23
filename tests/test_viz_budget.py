"""Slice 1 — dual-channel visualization helper tests.

These tests drive the helper with a fake ``save_fn`` that writes arbitrary
bytes, so no Graphviz binary is required and the tests stay hermetic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp.errors import GraphvizMissing, WorkspaceError
from pm4py_mcp.viz import (
    INLINE_IMAGE_BUDGET_BYTES,
    check_graphviz,
    save_dual_channel,
)


def _fake_save(payload_size: int):
    """Return a ``save_fn`` that writes ``payload_size`` bytes to the given path."""

    def save(path: str) -> None:
        Path(path).write_bytes(b"\x00" * payload_size)

    return save


def test_small_png_attaches_inline() -> None:
    result = save_dual_channel(_fake_save(100), stem="small", summary_text="ok")
    assert result.inline_attached is True
    content = result.as_content()
    # content = [text, Image]
    assert len(content) == 2
    assert content[0] == "ok"


def test_large_png_omitted_from_inline() -> None:
    huge = INLINE_IMAGE_BUDGET_BYTES + 1_000
    result = save_dual_channel(_fake_save(huge), stem="big", summary_text="big")
    assert result.inline_attached is False
    content = result.as_content()
    assert len(content) == 1  # text only, no image block
    assert content[0] == "big"


def test_paths_always_returned() -> None:
    """File paths are the channel that always works — never elide them."""
    huge = INLINE_IMAGE_BUDGET_BYTES + 1
    result = save_dual_channel(_fake_save(huge), stem="paths", summary_text="x")
    assert Path(result.png_path).exists()
    assert Path(result.svg_path).exists()
    assert result.png_path.endswith(".png")
    assert result.svg_path.endswith(".svg")


def test_png_and_svg_share_unique_suffix() -> None:
    result = save_dual_channel(_fake_save(10), stem="pair", summary_text="y")
    png = Path(result.png_path)
    svg = Path(result.svg_path)
    assert png.stem == svg.stem  # same unique suffix on both


def test_missing_file_raises_workspace_error(tmp_path: Path) -> None:
    """If save_fn silently succeeds without producing a file, we raise."""

    def silent_save(_: str) -> None:
        return None  # no-op; no file written

    with pytest.raises(WorkspaceError):
        save_dual_channel(silent_save, stem="phantom", summary_text="z")


def test_file_not_found_translated_to_graphviz_missing() -> None:
    """PM4Py's save raises FileNotFoundError when `dot` is missing; translate it."""

    def save_that_cant_find_dot(_: str) -> None:
        raise FileNotFoundError("[WinError 2] The system cannot find the file specified")

    with pytest.raises(GraphvizMissing):
        save_dual_channel(save_that_cant_find_dot, stem="no-dot", summary_text="z")


def test_check_graphviz_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        check_graphviz()


def test_check_graphviz_passes_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: "/usr/bin/dot")
    check_graphviz()  # should not raise
