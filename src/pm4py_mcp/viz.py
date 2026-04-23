"""Dual-channel visualization helper.

Every render tool saves **both** PNG and SVG to the workspace, returns a
text summary plus absolute paths, and attaches an inline PNG only when
the file fits under the Claude Desktop response-size budget (~700 KB,
well below the 1 MB hard cap to leave headroom for other content).

Claude Desktop renders inline PNGs in the collapsible tool-use accordion;
Claude Code renders nothing inline. File paths are the channel that always
works, so they are never omitted.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import Image

from pm4py_mcp.errors import GraphvizMissing, WorkspaceError
from pm4py_mcp.workspace import derived_path

# ~700 KB — well below the 1 MB Claude Desktop response ceiling.
INLINE_IMAGE_BUDGET_BYTES = 700_000


@dataclass(frozen=True)
class VizPayload:
    """Dual-channel render output.

    ``as_content`` returns a list shaped for FastMCP's tool-return convention:
    strings become TextContent blocks, ``Image`` objects become ImageContent
    blocks. See ``mcp.server.fastmcp.utilities.func_metadata._convert_to_content``.
    """

    text: str
    png_path: str
    svg_path: str
    inline_attached: bool

    def as_content(self) -> list[str | Image]:
        blocks: list[str | Image] = [self.text]
        if self.inline_attached:
            blocks.append(Image(path=self.png_path))
        return blocks


def check_graphviz() -> None:
    """Raise :class:`GraphvizMissing` if the ``dot`` binary is not on PATH.

    Called once per visualization tool before we hand off to PM4Py, which
    otherwise fails deep inside the Graphviz Python bindings with an opaque
    FileNotFoundError.
    """
    if shutil.which("dot") is None:
        raise GraphvizMissing(
            "The Graphviz `dot` binary was not found on PATH. Visualization tools "
            "require it in addition to PM4Py's Python bindings. Install from "
            "https://graphviz.org/download/ (Windows: winget install Graphviz; "
            "macOS: brew install graphviz; Ubuntu: apt install graphviz) and "
            "restart the MCP server."
        )


def save_dual_channel(
    save_fn: Callable[[str], None],
    stem: str,
    *,
    summary_text: str,
    budget_bytes: int = INLINE_IMAGE_BUDGET_BYTES,
) -> VizPayload:
    """Render an artifact in both PNG and SVG to the workspace.

    ``save_fn`` is called twice, once with an absolute PNG path and once with
    an SVG path. PM4Py's ``save_vis_*`` helpers dispatch on the file extension,
    so the same function works for both formats.

    Parameters
    ----------
    save_fn
        Callable that writes a visualization file at the given absolute path.
    stem
        Base filename (no extension, no path separators).
    summary_text
        Human-readable caption that always accompanies the render.
    budget_bytes
        PNG files larger than this are NOT attached inline; the path is still
        returned so users can open the file directly.
    """
    png_path = derived_path(stem, "png")
    svg_path = derived_path(stem, "svg", unique=False)
    # Keep PNG and SVG as a matched pair sharing the unique suffix.
    svg_path = png_path.with_suffix(".svg")

    try:
        save_fn(str(png_path))
    except FileNotFoundError as exc:
        # Graphviz dispatch error surfacing as a missing executable.
        raise GraphvizMissing(
            "PM4Py could not invoke Graphviz while saving PNG. "
            "Install `dot` from https://graphviz.org/download/ and retry."
        ) from exc

    try:
        save_fn(str(svg_path))
    except FileNotFoundError as exc:
        raise GraphvizMissing(
            "PM4Py could not invoke Graphviz while saving SVG. "
            "Install `dot` from https://graphviz.org/download/ and retry."
        ) from exc

    if not png_path.exists() or not svg_path.exists():
        raise WorkspaceError(
            f"Visualization save reported success but files are missing: "
            f"png={png_path.exists()}, svg={svg_path.exists()}"
        )

    inline_attached = png_path.stat().st_size <= budget_bytes

    return VizPayload(
        text=summary_text,
        png_path=str(png_path),
        svg_path=str(svg_path),
        inline_attached=inline_attached,
    )


def _read_png_bytes(path: Path | str) -> bytes:
    """Small helper kept separate so tests can monkeypatch if needed."""
    return Path(path).read_bytes()
