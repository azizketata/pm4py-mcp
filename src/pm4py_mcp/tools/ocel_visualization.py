"""Phase 2 Slice 2 — OCEL 2.0 visualization tools.

Renders object-centric DFGs and OCPNs via PM4Py's Graphviz backends. Uses the
same ``save_dual_channel`` helper and ``structured_output=False`` pattern as
the Phase 1 visualization tools, so responses remain a ``[caption, Image]``
content list rather than a schema-validated dict.
"""

from __future__ import annotations

from typing import Any

import pm4py
from mcp.server.fastmcp import Image

from pm4py_mcp.server import mcp, registry
from pm4py_mcp.viz import check_graphviz, save_dual_channel


def _as_content_blocks(text: str, png_path: str, attached: bool) -> list[Any]:
    blocks: list[Any] = [text]
    if attached:
        blocks.append(Image(path=png_path))
    return blocks


@mcp.tool(structured_output=False)
def visualize_ocdfg(ocdfg_id: str) -> list[Any]:
    """Render an OC-DFG (from ``discover_ocdfg``) as PNG + SVG.

    PM4Py colors the edges by object type, so the inline PNG visually separates
    the per-type flows. Frequency annotations are included by default.
    """
    _, payload = registry.get(ocdfg_id, expected_kind="ocdfg")
    check_graphviz()

    def _save(path: str) -> None:
        pm4py.save_vis_ocdfg(payload, path)

    result = save_dual_channel(_save, stem="ocdfg", summary_text="")

    obj_types = sorted(payload.get("object_types", set()))
    num_activities = len(payload.get("activities", set()))
    caption = (
        f"OC-DFG ({ocdfg_id}): {num_activities} activities, "
        f"{len(obj_types)} object types ({', '.join(obj_types)})\n"
        f"PNG: {result.png_path}\n"
        f"SVG: {result.svg_path}"
    )
    return _as_content_blocks(caption, result.png_path, result.inline_attached)


@mcp.tool(structured_output=False)
def visualize_oc_petri_net(ocpn_id: str) -> list[Any]:
    """Render an object-centric Petri net (from ``discover_oc_petri_net``) as PNG + SVG."""
    _, ocpn = registry.get(ocpn_id, expected_kind="ocpn")
    check_graphviz()

    def _save(path: str) -> None:
        pm4py.save_vis_ocpn(ocpn, path)

    result = save_dual_channel(_save, stem="ocpn", summary_text="")

    obj_types = sorted(ocpn.get("object_types", set()))
    # ``ocpn["petri_nets"]`` is the authoritative per-object-type breakdown.
    # OCPetriNet exposes a flat ``.places`` / ``.arcs`` attribute but it's not
    # accessible via dict-style ``ocpn["places"]``, so sum from petri_nets.
    total_places = sum(
        len(triple[0].places) for triple in ocpn.get("petri_nets", {}).values()
    )
    total_arcs = sum(
        len(triple[0].arcs) for triple in ocpn.get("petri_nets", {}).values()
    )
    caption = (
        f"OC Petri net ({ocpn_id}): {len(obj_types)} object types "
        f"({', '.join(obj_types)}), {total_places} places, {total_arcs} arcs\n"
        f"PNG: {result.png_path}\n"
        f"SVG: {result.svg_path}"
    )
    return _as_content_blocks(caption, result.png_path, result.inline_attached)


__all__ = ["visualize_oc_petri_net", "visualize_ocdfg"]
