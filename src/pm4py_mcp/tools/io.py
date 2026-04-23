"""Phase 1 — I/O and workspace tools.

Handles event logs at the boundary of the system: reading from disk,
summarizing on demand, and exporting back out. Never returns the event
log itself — always a handle (``log_id``) plus a compact summary.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pm4py
from mcp.server.fastmcp import Context

from pm4py_mcp.errors import UnsupportedFormat, WorkspaceError
from pm4py_mcp.models import ExportResult, LogSummary, WorkspaceEntry
from pm4py_mcp.server import mcp, registry
from pm4py_mcp.workspace import ensure_workspace

_Ctx = Context[Any, Any, Any]

# Progress-reporting threshold: files above this trigger ctx.report_progress.
_PROGRESS_THRESHOLD_BYTES = 10_000_000

_SUPPORTED_READ_FORMATS = ("xes", "xes.gz", "csv", "parquet")
_SUPPORTED_WRITE_FORMATS = ("xes", "csv")


def _infer_format(path: str, format: str | None) -> str:
    if format:
        return format.lower().lstrip(".")
    lower = path.lower()
    if lower.endswith(".xes.gz"):
        return "xes.gz"
    suffix = Path(lower).suffix.lstrip(".")
    if not suffix:
        raise UnsupportedFormat(
            f"Could not infer format from {path!r}; "
            f"pass format= explicitly (one of {_SUPPORTED_READ_FORMATS})."
        )
    return suffix


def _build_log_summary(log: pd.DataFrame, log_id: str) -> LogSummary:
    """Aggregate the describe_log / load_event_log return shape."""
    case_col = log["case:concept:name"]
    activity_col = log["concept:name"]
    ts_col = log["time:timestamp"]

    variants_dict = pm4py.get_variants(log)
    # variants_dict is {tuple[str, ...]: int} for DataFrame input.
    top = sorted(variants_dict.items(), key=lambda kv: -kv[1])[:5]
    top_variants = [{"trace": list(trace), "count": int(count)} for trace, count in top]

    activities_sorted = sorted(activity_col.unique().tolist())
    return LogSummary(
        log_id=log_id,
        num_cases=int(case_col.nunique()),
        num_events=len(log),
        num_activities=len(activities_sorted),
        activities_preview=activities_sorted[:20],
        time_range=(ts_col.min().isoformat(), ts_col.max().isoformat()),
        top_variants=top_variants,
    )


async def _maybe_progress(
    ctx: _Ctx | None, progress: float, total: float | None, message: str
) -> None:
    if ctx is None:
        return
    await ctx.report_progress(progress=progress, total=total, message=message)


@mcp.tool()
async def load_event_log(
    path: str,
    format: str | None = None,
    case_id_key: str = "case:concept:name",
    activity_key: str = "concept:name",
    timestamp_key: str = "time:timestamp",
    ctx: _Ctx | None = None,
) -> dict[str, Any]:
    """Read an event log from disk and store it under a fresh ``log_id`` handle.

    Format is inferred from the file extension when ``format`` is not passed.
    Supported: XES (``.xes``, ``.xes.gz``), CSV (``.csv``), Parquet (``.parquet``).

    For CSV and Parquet, the three ``*_key`` parameters tell pm4py which
    columns to treat as case id / activity / timestamp. Defaults assume the
    pm4py-standard column names.

    Returns a dict with ``log_id`` plus a compact summary (case/event counts,
    activities preview, time range, top 5 variants). Never returns the log
    itself — subsequent tools retrieve it by handle.
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Event log not found: {resolved}")

    fmt = _infer_format(str(resolved), format)
    size = resolved.stat().st_size
    emit_progress = size > _PROGRESS_THRESHOLD_BYTES

    if emit_progress:
        await _maybe_progress(ctx, 0.0, float(size), f"Reading {fmt} ({size // 1024} KB)")

    log: pd.DataFrame
    if fmt in ("xes", "xes.gz"):
        log = pm4py.read_xes(str(resolved))
    elif fmt == "csv":
        df = pd.read_csv(resolved)
        log = pm4py.format_dataframe(
            df,
            case_id=case_id_key,
            activity_key=activity_key,
            timestamp_key=timestamp_key,
        )
    elif fmt == "parquet":
        df = pd.read_parquet(resolved)
        log = pm4py.format_dataframe(
            df,
            case_id=case_id_key,
            activity_key=activity_key,
            timestamp_key=timestamp_key,
        )
    else:
        raise UnsupportedFormat(
            f"Unsupported read format {fmt!r}. Expected one of {_SUPPORTED_READ_FORMATS}."
        )

    if emit_progress:
        await _maybe_progress(ctx, float(size), float(size), "Summarizing")

    log_id = registry.put("log", log)
    summary = _build_log_summary(log, log_id)
    return summary.as_dict()


@mcp.tool()
def describe_log(log_id: str) -> dict[str, Any]:
    """Return the compact summary for a previously loaded log.

    Exact same shape as the summary attached to ``load_event_log``'s
    response, re-computed on demand. Raises :class:`HandleNotFound` if
    the registry has evicted the log (1-hour TTL or LRU overflow).
    """
    _, log = registry.get(log_id, expected_kind="log")
    return _build_log_summary(cast(pd.DataFrame, log), log_id).as_dict()


@mcp.tool()
def export_log(log_id: str, format: str, path: str) -> dict[str, Any]:
    """Write a log from the registry to disk.

    ``format`` must be ``"xes"`` or ``"csv"``. If ``path`` has no directory
    component, the file lands in the workspace; otherwise the given path
    (absolute or relative to CWD) is used verbatim.
    """
    fmt = format.lower().lstrip(".")
    if fmt not in _SUPPORTED_WRITE_FORMATS:
        raise UnsupportedFormat(
            f"Unsupported write format {fmt!r}. Expected one of {_SUPPORTED_WRITE_FORMATS}."
        )

    _, log_obj = registry.get(log_id, expected_kind="log")
    log = cast(pd.DataFrame, log_obj)

    p = Path(path).expanduser()
    # bare filename → put in workspace; otherwise honor the path as-is
    out = ensure_workspace() / p if len(p.parts) == 1 else p.resolve()

    # Ensure correct extension
    expected_ext = f".{fmt}"
    if out.suffix.lower() != expected_ext:
        out = out.with_suffix(expected_ext)

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(f"Could not create output directory {out.parent}: {exc}") from exc

    if fmt == "xes":
        pm4py.write_xes(log, str(out))
    elif fmt == "csv":
        log.to_csv(out, index=False)

    if not out.exists():
        raise WorkspaceError(f"Export reported success but file is missing: {out}")

    return ExportResult(
        path=str(out),
        format=fmt,
        size_bytes=out.stat().st_size,
    ).as_dict()


@mcp.tool()
def list_workspace() -> dict[str, Any]:
    """List files currently in the workspace directory.

    Reports each entry's name, absolute path, size, and modification time.
    Subdirectories are included by name but not recursed into.
    """
    base = ensure_workspace()
    entries: list[dict[str, Any]] = []
    for item in sorted(base.iterdir()):
        stat = item.stat()
        entries.append(
            WorkspaceEntry(
                name=item.name,
                path=str(item),
                size_bytes=stat.st_size,
                modified=_dt.datetime.fromtimestamp(stat.st_mtime, tz=_dt.timezone.utc).isoformat(),
            ).as_dict()
        )
    return {
        "workspace": str(base),
        "count": len(entries),
        "entries": entries,
    }


# Re-export for convenient direct-call testing.
__all__ = [
    "describe_log",
    "export_log",
    "list_workspace",
    "load_event_log",
]
