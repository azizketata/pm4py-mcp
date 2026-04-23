"""Phase 2 Slice 2 — OCEL visualization tool unit tests.

Mirrors the Phase 1 visualization test pattern: real-render tests are gated
on ``dot`` being on PATH, error-translation tests run unconditionally via
monkeypatching ``shutil.which``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mcp.server.fastmcp import Image

from pm4py_mcp.errors import GraphvizMissing, InvalidKind
from pm4py_mcp.server import registry
from pm4py_mcp.tools.ocel_discovery import (
    discover_oc_petri_net,
    discover_ocdfg,
)
from pm4py_mcp.tools.ocel_visualization import (
    visualize_oc_petri_net,
    visualize_ocdfg,
)
from tests.fixtures import tiny_ocel

needs_graphviz = pytest.mark.skipif(
    shutil.which("dot") is None,
    reason="Graphviz `dot` binary not installed; real rendering skipped",
)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


@pytest.fixture
def ocel_id() -> str:
    return registry.put("ocel", tiny_ocel())


# --- error translation (runs without Graphviz installed) ---


def test_visualize_ocdfg_raises_when_dot_missing(
    ocel_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    ocdfg_id = discover_ocdfg(ocel_id)["ocdfg_id"]
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        visualize_ocdfg(ocdfg_id)


def test_visualize_oc_petri_net_raises_when_dot_missing(
    ocel_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    ocpn_id = discover_oc_petri_net(ocel_id)["ocpn_id"]
    monkeypatch.setattr("pm4py_mcp.viz.shutil.which", lambda _: None)
    with pytest.raises(GraphvizMissing):
        visualize_oc_petri_net(ocpn_id)


def test_visualize_ocdfg_rejects_wrong_kind(ocel_id: str) -> None:
    """Passing an ocel_id to the DFG renderer raises InvalidKind (before Graphviz check)."""
    with pytest.raises(InvalidKind):
        visualize_ocdfg(ocel_id)


def test_visualize_oc_petri_net_rejects_wrong_kind(ocel_id: str) -> None:
    with pytest.raises(InvalidKind):
        visualize_oc_petri_net(ocel_id)


# --- real rendering (only when Graphviz is installed) ---


@needs_graphviz
def test_visualize_ocdfg_real_render(ocel_id: str) -> None:
    ocdfg_id = discover_ocdfg(ocel_id)["ocdfg_id"]
    blocks = visualize_ocdfg(ocdfg_id)
    _assert_render_blocks(blocks, expect_substring="OC-DFG")


@needs_graphviz
def test_visualize_oc_petri_net_real_render(ocel_id: str) -> None:
    ocpn_id = discover_oc_petri_net(ocel_id)["ocpn_id"]
    blocks = visualize_oc_petri_net(ocpn_id)
    _assert_render_blocks(blocks, expect_substring="OC Petri net")


@needs_graphviz
def test_visualize_ocdfg_caption_lists_object_types(ocel_id: str) -> None:
    ocdfg_id = discover_ocdfg(ocel_id)["ocdfg_id"]
    blocks = visualize_ocdfg(ocdfg_id)
    caption = blocks[0]
    assert isinstance(caption, str)
    for ot in ("order", "item", "delivery"):
        assert ot in caption
    assert "PNG:" in caption
    assert "SVG:" in caption


# --- helpers ---


def _assert_render_blocks(blocks: list, expect_substring: str) -> None:  # type: ignore[type-arg]
    """Shared assertion for successful dual-channel OCEL renders."""
    assert isinstance(blocks[0], str)
    assert expect_substring in blocks[0]
    assert len(blocks) == 2
    assert isinstance(blocks[1], Image)

    # Files on disk
    caption = blocks[0]
    png_line = next(line for line in caption.splitlines() if line.startswith("PNG:"))
    svg_line = next(line for line in caption.splitlines() if line.startswith("SVG:"))
    png = Path(png_line.removeprefix("PNG: ").strip())
    svg = Path(svg_line.removeprefix("SVG: ").strip())
    assert png.exists() and png.stat().st_size > 0
    assert svg.exists() and svg.stat().st_size > 0
