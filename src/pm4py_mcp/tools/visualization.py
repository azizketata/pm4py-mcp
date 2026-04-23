"""Phase 1 — visualization tools.

Each tool looks up a model in the registry, delegates to ``save_dual_channel``
(which writes both PNG and SVG to the workspace), and returns a FastMCP
content list: a short text caption followed by an inline PNG when it fits
under the response-size budget, otherwise text only. File paths are always
embedded in the caption so users can open artifacts directly regardless of
whether their MCP client renders inline images.
"""

from __future__ import annotations

from typing import Any

import pm4py
from mcp.server.fastmcp import Image

from pm4py_mcp.server import mcp, registry
from pm4py_mcp.viz import check_graphviz, save_dual_channel


def _build_blocks(caption: str, png_path: str, inline: bool) -> list[Any]:
    """FastMCP return convention: a list mixing strings (→ TextContent) and
    ``Image`` objects (→ ImageContent). See ``_convert_to_content`` in
    ``mcp.server.fastmcp.utilities.func_metadata``.
    """
    blocks: list[Any] = [caption]
    if inline:
        blocks.append(Image(path=png_path))
    return blocks


def _caption(header: str, png: str, svg: str) -> str:
    return f"{header}\nPNG: {png}\nSVG: {svg}"


@mcp.tool(structured_output=False)
def visualize_petri_net(petri_id: str) -> list[Any]:
    """Render a Petri net (from ``discover_petri_net``) as PNG + SVG."""
    _, payload = registry.get(petri_id, expected_kind="petri_net")
    check_graphviz()
    net, im, fm = payload

    def _save(path: str) -> None:
        pm4py.save_vis_petri_net(net, im, fm, path)

    result = save_dual_channel(_save, stem="petri-net", summary_text="")
    caption = _caption(
        f"Petri net ({petri_id}): "
        f"{len(net.places)} places, "
        f"{len(net.transitions)} transitions, "
        f"{len(net.arcs)} arcs",
        result.png_path,
        result.svg_path,
    )
    return _build_blocks(caption, result.png_path, result.inline_attached)


@mcp.tool(structured_output=False)
def visualize_dfg(dfg_id: str) -> list[Any]:
    """Render a directly-follows graph (from ``discover_dfg``) as PNG + SVG."""
    _, payload = registry.get(dfg_id, expected_kind="dfg")
    check_graphviz()
    dfg = payload["dfg"]
    starts = payload["start_activities"]
    ends = payload["end_activities"]

    def _save(path: str) -> None:
        pm4py.save_vis_dfg(dfg, starts, ends, path)

    result = save_dual_channel(_save, stem="dfg", summary_text="")
    caption = _caption(
        f"DFG ({dfg_id}): {len(dfg)} edges, "
        f"{len(starts)} start activities, {len(ends)} end activities",
        result.png_path,
        result.svg_path,
    )
    return _build_blocks(caption, result.png_path, result.inline_attached)


@mcp.tool(structured_output=False)
def visualize_process_tree(tree_id: str) -> list[Any]:
    """Render a process tree (from ``discover_process_tree``) as PNG + SVG."""
    _, tree = registry.get(tree_id, expected_kind="process_tree")
    check_graphviz()

    def _save(path: str) -> None:
        pm4py.save_vis_process_tree(tree, path)

    result = save_dual_channel(_save, stem="process-tree", summary_text="")
    caption = _caption(
        f"Process tree ({tree_id})",
        result.png_path,
        result.svg_path,
    )
    return _build_blocks(caption, result.png_path, result.inline_attached)


@mcp.tool(structured_output=False)
def visualize_bpmn(bpmn_id: str) -> list[Any]:
    """Render a BPMN diagram (from ``discover_bpmn``) as PNG + SVG."""
    _, bpmn = registry.get(bpmn_id, expected_kind="bpmn")
    check_graphviz()

    def _save(path: str) -> None:
        pm4py.save_vis_bpmn(bpmn, path)

    result = save_dual_channel(_save, stem="bpmn", summary_text="")
    nodes = list(bpmn.get_nodes())
    flows = list(bpmn.get_flows())
    caption = _caption(
        f"BPMN ({bpmn_id}): {len(nodes)} nodes, {len(flows)} flows",
        result.png_path,
        result.svg_path,
    )
    return _build_blocks(caption, result.png_path, result.inline_attached)


__all__ = [
    "visualize_bpmn",
    "visualize_dfg",
    "visualize_petri_net",
    "visualize_process_tree",
]
