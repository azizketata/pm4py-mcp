"""Matplotlib-backed single-channel PNG rendering.

Parallel to ``viz.py::save_dual_channel``. Kept as a separate module so the
Graphviz-specific error handling in ``viz.py`` stays simple — Graphviz and
matplotlib have genuinely different failure modes and should not be
multiplexed behind a ``backend:`` parameter.

PNG-only by design: matplotlib SVG exports are pathological for dotted
charts (one ``<line>`` element per event, tens of thousands on a real log).
The inline-attachment budget rule (~700 KB) still applies, matching
``save_dual_channel``'s convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pm4py_mcp.errors import WorkspaceError
from pm4py_mcp.workspace import derived_path

INLINE_BUDGET_BYTES = 700_000


@dataclass(frozen=True)
class MatplotlibVizPayload:
    """Return shape for matplotlib-backed viz tools.

    Parallel to ``viz.VizPayload`` but without an SVG path — matplotlib
    SVG exports are impractical for the charts we use this helper for.
    """

    png_path: str
    inline_attached: bool


def save_matplotlib_png(
    save_fn: Callable[[str], None],
    *,
    stem: str,
) -> MatplotlibVizPayload:
    """Save a matplotlib-backed PNG to the workspace and decide on inline.

    ``save_fn`` receives the absolute target path and must produce a file
    there. Raises :class:`WorkspaceError` if the file is missing after the
    call (mirrors ``save_dual_channel``'s safety check).

    Budgets inline attachment at 700 KB (matching the Graphviz helper).
    """
    png = derived_path(stem, ".png")
    save_fn(str(png))
    png_path = Path(png)
    if not png_path.is_file():
        raise WorkspaceError(
            f"save_fn reported success but file is missing: {png_path}"
        )
    inline = png_path.stat().st_size <= INLINE_BUDGET_BYTES
    return MatplotlibVizPayload(png_path=str(png_path), inline_attached=inline)


__all__ = ["INLINE_BUDGET_BYTES", "MatplotlibVizPayload", "save_matplotlib_png"]
