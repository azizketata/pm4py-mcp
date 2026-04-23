"""Phase 3 Slice 4 — unit tests for ``render_report``."""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp import __version__
from pm4py_mcp.errors import WorkspaceError
from pm4py_mcp.tools.reports import render_report


@pytest.fixture(autouse=True)
def _isolate_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the workspace at tmp_path so generated reports don't litter home dir."""
    monkeypatch.setenv("PM4PY_MCP_WORKSPACE", str(tmp_path))


def test_render_report_writes_markdown_with_title_and_findings() -> None:
    result = render_report(
        title="Q1 Process Review",
        findings="The process looks healthy. Median cycle time is 3.2 days.",
    )
    out = Path(result["path"])
    assert out.is_file()
    assert out.suffix == ".md"
    assert result["size_bytes"] > 0
    assert result["num_artifacts"] == 0

    body = out.read_text(encoding="utf-8")
    assert body.startswith("# Q1 Process Review")
    assert "Median cycle time is 3.2 days." in body
    assert __version__ in body


def test_render_report_embeds_image_artifacts(tmp_path: Path) -> None:
    # Create a fake PNG + fake SVG so the paths pass through, and a CSV link.
    png = tmp_path / "petri.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    svg = tmp_path / "dfg.svg"
    svg.write_text("<svg/>", encoding="utf-8")
    csv = tmp_path / "durations.csv"
    csv.write_text("case,duration\nc1,3.0\n", encoding="utf-8")

    result = render_report(
        title="With Artifacts",
        findings="See attached diagrams and durations export.",
        artifact_paths=[str(png), str(svg), str(csv)],
    )
    assert result["num_artifacts"] == 3

    body = Path(result["path"]).read_text(encoding="utf-8")
    assert "## Artifacts" in body
    # Images get embedded as ![...](...)
    assert f"![petri.png]({png.as_posix()})" in body
    assert f"![dfg.svg]({svg.as_posix()})" in body
    # Non-images get listed as links
    assert f"- [durations.csv]({csv.as_posix()})" in body


def test_render_report_respects_custom_output_path(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "exec.md"
    result = render_report(
        title="Executive Summary",
        findings="Body.",
        output_path=str(target),
    )
    assert Path(result["path"]) == target.resolve()
    assert target.is_file()


def test_render_report_adds_md_extension_when_missing(tmp_path: Path) -> None:
    target = tmp_path / "report-no-ext"
    result = render_report(
        title="T",
        findings="F",
        output_path=str(target),
    )
    assert Path(result["path"]).suffix == ".md"
    assert Path(result["path"]).name == "report-no-ext.md"


def test_render_report_bare_filename_lands_in_workspace(tmp_path: Path) -> None:
    # Workspace was redirected to tmp_path by the autouse fixture.
    result = render_report(
        title="Title",
        findings="Findings.",
        output_path="my-report.md",
    )
    out = Path(result["path"])
    assert out.parent == tmp_path
    assert out.name == "my-report.md"


def test_render_report_default_output_is_workspace_unique_file(tmp_path: Path) -> None:
    r1 = render_report(title="A", findings="x")
    r2 = render_report(title="B", findings="y")
    assert r1["path"] != r2["path"]
    for r in (r1, r2):
        out = Path(r["path"])
        assert out.parent == tmp_path
        assert out.name.startswith("report-")
        assert out.suffix == ".md"


def test_render_report_empty_title_raises() -> None:
    with pytest.raises(WorkspaceError, match="title"):
        render_report(title="   ", findings="ok")


def test_render_report_empty_findings_raises() -> None:
    with pytest.raises(WorkspaceError, match="findings"):
        render_report(title="Title", findings="")


def test_render_report_includes_iso_timestamp() -> None:
    result = render_report(title="T", findings="F")
    body = Path(result["path"]).read_text(encoding="utf-8")
    # ISO-8601 with seconds precision, UTC
    assert "Generated " in body
    assert "+00:00" in body or "Z" in body


def test_render_report_without_artifacts_omits_artifacts_header() -> None:
    result = render_report(title="T", findings="F")
    body = Path(result["path"]).read_text(encoding="utf-8")
    assert "## Artifacts" not in body
