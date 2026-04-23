"""Slice 2 — I/O tool unit tests.

Calls the tool functions directly; the in-process ClientSession layer is
exercised separately in ``test_tools_mcp.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pm4py_mcp.errors import HandleNotFound, InvalidKind, UnsupportedFormat
from pm4py_mcp.server import registry
from pm4py_mcp.tools.io import (
    describe_log,
    export_log,
    list_workspace,
    load_event_log,
)
from tests.fixtures import tiny_log, tiny_log_xes


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Phase-1 tests share a process-wide singleton registry; keep it tidy."""
    registry.clear()


async def test_load_xes_returns_summary_and_handle(tmp_path: Path) -> None:
    xes_path = tiny_log_xes(tmp_path)
    summary = await load_event_log(str(xes_path))

    assert summary["log_id"].startswith("log-")
    assert summary["num_cases"] == 3
    assert summary["num_events"] == 11
    assert summary["num_activities"] == 4
    assert set(summary["activities_preview"]) == {"register", "triage", "treat", "discharge"}
    assert len(summary["top_variants"]) <= 5
    assert summary["log_id"] in registry


async def test_load_csv_with_column_mapping(tmp_path: Path) -> None:
    csv_path = tmp_path / "tiny.csv"
    # Write a CSV with non-pm4py column names to exercise the override kwargs.
    import pandas as pd

    pd.DataFrame(
        [
            ("c1", "a", "2024-01-01T08:00:00"),
            ("c1", "b", "2024-01-01T08:30:00"),
            ("c2", "a", "2024-01-01T09:00:00"),
        ],
        columns=["caseid", "act", "ts"],
    ).to_csv(csv_path, index=False)

    summary = await load_event_log(
        str(csv_path),
        case_id_key="caseid",
        activity_key="act",
        timestamp_key="ts",
    )
    assert summary["num_cases"] == 2
    assert summary["num_events"] == 3


async def test_load_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        await load_event_log("/nonexistent/path/to/file.xes")


async def test_load_unknown_extension_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "log.weird"
    bogus.write_text("garbage")
    with pytest.raises(UnsupportedFormat):
        await load_event_log(str(bogus))


async def test_describe_log_matches_load_summary(tmp_path: Path) -> None:
    xes_path = tiny_log_xes(tmp_path)
    load_summary = await load_event_log(str(xes_path))
    desc_summary = describe_log(load_summary["log_id"])

    # Everything except maybe key ordering should match exactly.
    assert desc_summary == load_summary


def test_describe_log_missing_handle_raises() -> None:
    with pytest.raises(HandleNotFound):
        describe_log("log-doesnotexist")


def test_describe_log_wrong_kind_raises() -> None:
    h = registry.put("petri_net", object())
    with pytest.raises(InvalidKind):
        describe_log(h)


def test_export_log_xes_to_workspace() -> None:
    log = tiny_log()
    log_id = registry.put("log", log)

    result = export_log(log_id, format="xes", path="exported")
    out = Path(result["path"])

    assert out.exists()
    assert out.suffix == ".xes"
    assert result["format"] == "xes"
    assert result["size_bytes"] > 0


def test_export_log_csv_to_workspace() -> None:
    log = tiny_log()
    log_id = registry.put("log", log)

    result = export_log(log_id, format="csv", path="exported")
    out = Path(result["path"])

    assert out.exists()
    assert out.suffix == ".csv"
    # Must contain header + 10 data rows
    assert out.read_text().count("\n") >= 10


def test_export_log_absolute_path_honored(tmp_path: Path) -> None:
    log = tiny_log()
    log_id = registry.put("log", log)

    target = tmp_path / "nested" / "out"
    result = export_log(log_id, format="xes", path=str(target))
    out = Path(result["path"])
    assert out.is_relative_to(tmp_path)
    assert out.exists()


def test_export_log_unsupported_format() -> None:
    log = tiny_log()
    log_id = registry.put("log", log)
    with pytest.raises(UnsupportedFormat):
        export_log(log_id, format="parquet", path="out")


def test_list_workspace_reports_exported_files() -> None:
    log = tiny_log()
    log_id = registry.put("log", log)
    export_log(log_id, format="xes", path="listing-test")

    result = list_workspace()

    assert result["count"] >= 1
    names = [e["name"] for e in result["entries"]]
    assert any(name.startswith("listing-test") for name in names)
    for entry in result["entries"]:
        assert Path(entry["path"]).is_absolute()
        assert entry["size_bytes"] >= 0


def test_list_workspace_empty_when_nothing_written() -> None:
    result = list_workspace()
    assert result["count"] == 0
    assert result["entries"] == []
