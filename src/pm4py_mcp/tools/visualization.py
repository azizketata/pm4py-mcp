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

from pm4py_mcp._matplotlib import save_matplotlib_png
from pm4py_mcp.errors import UnsupportedFormat
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


@mcp.tool(structured_output=False)
def visualize_powl(powl_id: str) -> list[Any]:
    """Render a POWL model (from ``discover_powl``) as PNG + SVG.

    Graphviz-backed. POWL diagrams show partial-order edges between
    sub-workflows; the root operator is reported in the caption.
    """
    _, powl = registry.get(powl_id, expected_kind="powl")
    check_graphviz()

    def _save(path: str) -> None:
        pm4py.save_vis_powl(powl, path)

    result = save_dual_channel(_save, stem="powl", summary_text="")
    root_op = type(powl).__name__
    num_children = len(getattr(powl, "children", []) or [])
    caption = _caption(
        f"POWL ({powl_id}): root={root_op}, {num_children} top-level children",
        result.png_path,
        result.svg_path,
    )
    return _build_blocks(caption, result.png_path, result.inline_attached)


# --- 0.4.1: matplotlib-backed advanced visualizations ---


_DEFAULT_DOTTED_CHART_ATTRS: list[str] = ["concept:name", "time:timestamp"]


@mcp.tool(structured_output=False)
def visualize_dotted_chart(
    log_id: str,
    attributes: list[str] | None = None,
) -> list[Any]:
    """Render a dotted chart (matplotlib, PNG-only).

    Dotted charts project events onto a time-vs-value scatter using the
    provided ``attributes``. Default ``["concept:name", "time:timestamp"]``
    plots activity versus event time — the most useful view on an unfamiliar
    log. Pass other attribute names (e.g. ``["org:resource", "time:timestamp"]``)
    to see resource timelines or any numeric/categorical column.

    No Graphviz dependency — matplotlib is a pm4py runtime dep.
    """
    _, log = registry.get(log_id, expected_kind="log")
    attrs = list(attributes) if attributes is not None else list(_DEFAULT_DOTTED_CHART_ATTRS)

    # Validate every attribute is present to fail fast with a helpful message
    # instead of letting pm4py surface a cryptic KeyError.
    available = set(log.columns)
    missing = [a for a in attrs if a not in available]
    if missing:
        raise UnsupportedFormat(
            f"Dotted-chart attributes not found in log: {missing}. "
            f"Available columns (first 20): {sorted(available)[:20]}."
        )

    def _save(path: str) -> None:
        pm4py.save_vis_dotted_chart(log, path, attributes=attrs)

    result = save_matplotlib_png(_save, stem="dotted-chart")
    caption = (
        f"Dotted chart ({log_id}), attributes={attrs}\n"
        f"PNG: {result.png_path}"
    )
    blocks: list[Any] = [caption]
    if result.inline_attached:
        blocks.append(Image(path=result.png_path))
    return blocks


@mcp.tool(structured_output=False)
def visualize_performance_spectrum(
    log_id: str,
    activities: list[str],
) -> list[Any]:
    """Render a performance spectrum (matplotlib, PNG-only).

    Plots the duration of each case along an ordered activity list, revealing
    bottleneck segments visually. ``activities`` is required — the chart is
    only meaningful when the caller picks a subset of activities to track.
    Typically the activities of interest from the dominant variant(s).

    No Graphviz dependency — matplotlib is a pm4py runtime dep.
    """
    _, log = registry.get(log_id, expected_kind="log")
    if not activities:
        raise UnsupportedFormat(
            "visualize_performance_spectrum requires a non-empty 'activities' list."
        )

    activity_col = log.get("concept:name")
    if activity_col is None:
        raise UnsupportedFormat("Log is missing 'concept:name' column.")
    available = set(activity_col.unique().tolist())
    missing = [a for a in activities if a not in available]
    if missing:
        raise UnsupportedFormat(
            f"Activities not found in log: {missing}. "
            f"Available activities (first 20): {sorted(available)[:20]}."
        )

    def _save(path: str) -> None:
        pm4py.save_vis_performance_spectrum(log, activities, path)

    result = save_matplotlib_png(_save, stem="perf-spectrum")
    caption = (
        f"Performance spectrum ({log_id}), activities={activities}\n"
        f"PNG: {result.png_path}"
    )
    blocks: list[Any] = [caption]
    if result.inline_attached:
        blocks.append(Image(path=result.png_path))
    return blocks


__all__ = [
    "visualize_bpmn",
    "visualize_dfg",
    "visualize_dotted_chart",
    "visualize_performance_spectrum",
    "visualize_petri_net",
    "visualize_powl",
    "visualize_process_tree",
]
