"""Slice 3 — visualization tool unit tests.

Uses a conditional-skip pattern: real rendering requires the Graphviz `dot`
binary on PATH; tests that need it are decorated with ``needs_graphviz``
and will be skipped (not failed) when it's missing. Tests that verify error
translation (``GraphvizMissing`` when dot is absent) run unconditionally via
monkeypatching.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mcp.server.fastmcp import Image

from pm4py_mcp.errors import GraphvizMissing, InvalidKind
from pm4py_mcp.server import registry
from pm4py_mcp.tools.discovery import (
    discover_bpmn,
    discover_dfg,
    discover_petri_net,
    discover_process_tree,
)
from pm4py_mcp.tools.visualization import (
    visualize_bpmn,
    visualize_dfg,
    visualize_petri_net,
    visualize_process_tree,
)
from tests.fixtures import tiny_log

needs_graphviz = pytest.mark.skipif(
    shutil.which("dot") is None,
    reason="Graphviz `dot` binary not installed; real rendering skipped",
)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def log_id() -> str:
    return registry.put("log", tiny_log())


# --- error translation (runs without Graphviz installed) ---


def test_visualize_petri_net_raises_when_dot_missing(
    log_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        visualize_petri_net(petri_id)


def test_visualize_dfg_raises_when_dot_missing(
    log_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    dfg_id = discover_dfg(log_id)["dfg_id"]
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        visualize_dfg(dfg_id)


def test_visualize_process_tree_raises_when_dot_missing(
    log_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree_id = discover_process_tree(log_id)["tree_id"]
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        visualize_process_tree(tree_id)


def test_visualize_bpmn_raises_when_dot_missing(
    log_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    bpmn_id = discover_bpmn(log_id)["bpmn_id"]
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        visualize_bpmn(bpmn_id)


def test_visualize_rejects_wrong_kind(log_id: str) -> None:
    """Passing a log_id to a viz tool that expects a model raises InvalidKind."""
    with pytest.raises(InvalidKind):
        visualize_petri_net(log_id)


# --- real rendering (only when Graphviz is installed) ---


@needs_graphviz
def test_visualize_petri_net_real_render(log_id: str) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    blocks = visualize_petri_net(petri_id)
    _assert_render_blocks(blocks)


@needs_graphviz
def test_visualize_dfg_real_render(log_id: str) -> None:
    dfg_id = discover_dfg(log_id)["dfg_id"]
    blocks = visualize_dfg(dfg_id)
    _assert_render_blocks(blocks)


@needs_graphviz
def test_visualize_process_tree_real_render(log_id: str) -> None:
    tree_id = discover_process_tree(log_id)["tree_id"]
    blocks = visualize_process_tree(tree_id)
    _assert_render_blocks(blocks)


@needs_graphviz
def test_visualize_bpmn_real_render(log_id: str) -> None:
    bpmn_id = discover_bpmn(log_id)["bpmn_id"]
    blocks = visualize_bpmn(bpmn_id)
    _assert_render_blocks(blocks)


@needs_graphviz
def test_visualize_petri_net_caption_includes_paths(log_id: str) -> None:
    petri_id = discover_petri_net(log_id)["petri_id"]
    blocks = visualize_petri_net(petri_id)
    caption = blocks[0]
    assert isinstance(caption, str)
    assert "PNG:" in caption
    assert "SVG:" in caption
    assert petri_id in caption


# --- helpers ---


def _assert_render_blocks(blocks: list) -> None:  # type: ignore[type-arg]
    """Common assertions for a successful dual-channel render."""
    # Block 0 is always the text caption.
    assert isinstance(blocks[0], str)
    # The tiny log should render well under the inline budget, so block 1
    # must be an Image.
    assert len(blocks) == 2
    assert isinstance(blocks[1], Image)

    caption = blocks[0]
    # Extract paths from the caption and verify the files exist on disk.
    png_line = next(line for line in caption.splitlines() if line.startswith("PNG:"))
    svg_line = next(line for line in caption.splitlines() if line.startswith("SVG:"))
    png_path = Path(png_line.removeprefix("PNG: ").strip())
    svg_path = Path(svg_line.removeprefix("SVG: ").strip())
    assert png_path.exists()
    assert svg_path.exists()
    assert png_path.stat().st_size > 0
    assert svg_path.stat().st_size > 0
