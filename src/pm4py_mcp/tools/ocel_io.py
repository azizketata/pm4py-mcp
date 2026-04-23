"""Phase 2 — OCEL 2.0 I/O and the flatten bridge.

``flatten_ocel`` is the architectural centerpiece of Phase 2: it takes an
OCEL handle and a target object type, and returns a traditional ``log_id``
handle that composes with every Phase 1 tool (discover, conform, filter,
visualize). That composability is what lets pm4py-mcp offer object-centric
process mining without duplicating the Phase 1 tool surface for OCELs.

Never returns the OCEL itself — always a handle plus a compact summary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd
import pm4py
from pm4py.objects.ocel.obj import OCEL

from pm4py_mcp.errors import OptionalDepMissing, UnsupportedFormat, WorkspaceError
from pm4py_mcp.models import OcelExportResult, OcelSummary
from pm4py_mcp.server import mcp, registry
from pm4py_mcp.workspace import ensure_workspace

_OCEL_READ_FORMATS = ("jsonocel", "xmlocel", "sqlite")
_OCEL_WRITE_FORMATS = ("jsonocel", "xmlocel", "sqlite")

# How many activities / object types to preview in a summary before truncating.
_PREVIEW_CAP = 20
_TOP_OBJECT_TYPES_CAP = 10


def _infer_ocel_format(path: str) -> str:
    """Return the OCEL file format inferred from the path extension."""
    lower = path.lower()
    if lower.endswith(".jsonocel") or lower.endswith(".json"):
        return "jsonocel"
    if lower.endswith(".xmlocel") or lower.endswith(".xml"):
        return "xmlocel"
    if lower.endswith(".sqlite"):
        return "sqlite"
    raise UnsupportedFormat(
        f"Could not infer OCEL format from {path!r}; expected one of {_OCEL_READ_FORMATS}"
    )


def _build_ocel_summary(ocel: OCEL, ocel_id: str) -> OcelSummary:
    """Aggregate the compact summary attached to load/describe responses."""
    num_events = len(ocel.events)
    num_objects = len(ocel.objects)

    object_types_all = sorted(pm4py.ocel_get_object_types(ocel))
    object_types_preview = object_types_all[:_PREVIEW_CAP]

    # Events per object type: count distinct eids per type via the relations table.
    if len(ocel.relations) > 0 and {"ocel:type", "ocel:eid"}.issubset(ocel.relations.columns):
        counts_by_type = ocel.relations.groupby("ocel:type")["ocel:eid"].nunique().to_dict()
    else:
        counts_by_type = {}
    events_per_type = dict(
        sorted(counts_by_type.items(), key=lambda kv: -int(kv[1]))[:_TOP_OBJECT_TYPES_CAP]
    )
    events_per_type = {str(k): int(v) for k, v in events_per_type.items()}

    activities_all = sorted(ocel.events["ocel:activity"].dropna().unique().tolist())
    num_activities = len(activities_all)
    activities_preview = activities_all[:_PREVIEW_CAP]

    ts_col = ocel.events["ocel:timestamp"]
    time_range = (ts_col.min().isoformat(), ts_col.max().isoformat())

    return OcelSummary(
        ocel_id=ocel_id,
        num_events=num_events,
        num_objects=num_objects,
        num_object_types=len(object_types_all),
        object_types=object_types_preview,
        events_per_object_type=events_per_type,
        num_activities=num_activities,
        activities_preview=activities_preview,
        time_range=time_range,
    )


@mcp.tool()
def load_ocel(path: str) -> dict[str, Any]:
    """Read an OCEL 2.0 file from disk and store it under a fresh ``ocel_id`` handle.

    Format is inferred from the file extension:

    - ``.jsonocel`` / ``.json`` — JSON-OCEL (the most common format)
    - ``.xmlocel`` / ``.xml`` — XML-OCEL
    - ``.sqlite`` — SQLite-OCEL

    Returns a dict with ``ocel_id`` plus a compact summary (object types + per-type
    event counts, activities preview, time range). Never returns the OCEL itself;
    subsequent tools retrieve it by handle.

    Use ``flatten_ocel`` to project the OCEL onto a single object type and obtain
    a traditional ``log_id`` that composes with every Phase 1 tool.
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"OCEL file not found: {resolved}")

    fmt = _infer_ocel_format(str(resolved))

    try:
        ocel: OCEL = pm4py.read_ocel2(str(resolved))
    except ModuleNotFoundError as exc:
        if exc.name == "pyarrow":
            raise OptionalDepMissing("pyarrow", "pip install 'pm4py-mcp[ocel]'") from exc
        raise

    ocel_id = registry.put("ocel", ocel)
    summary = _build_ocel_summary(ocel, ocel_id)
    payload = summary.as_dict()
    payload["format"] = fmt
    return payload


@mcp.tool()
def describe_ocel(ocel_id: str) -> dict[str, Any]:
    """Return the compact summary for a previously loaded OCEL.

    Exact same shape as the summary attached to ``load_ocel``'s response,
    re-computed on demand. Raises :class:`HandleNotFound` if the registry
    evicted the OCEL (1-hour TTL or LRU overflow).
    """
    _, ocel = registry.get(ocel_id, expected_kind="ocel")
    return _build_ocel_summary(cast(OCEL, ocel), ocel_id).as_dict()


@mcp.tool()
def flatten_ocel(ocel_id: str, object_type: str) -> dict[str, Any]:
    """Project an OCEL onto a single object type and return a traditional log handle.

    **This is the Phase 2 composability bridge.** The resulting ``log_id`` works
    with every Phase 1 tool — discover, conform, filter, visualize.

    Raises :class:`UnsupportedFormat` if ``object_type`` is not present in the OCEL.
    """
    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)

    valid_types = pm4py.ocel_get_object_types(ocel)
    if object_type not in valid_types:
        raise UnsupportedFormat(
            f"Object type {object_type!r} not in OCEL {ocel_id}. "
            f"Available object types: {sorted(valid_types)}"
        )

    flat: pd.DataFrame = pm4py.ocel_flattening(ocel, object_type)
    new_log_id = registry.put("log", flat)

    num_cases = int(flat["case:concept:name"].nunique())
    num_events = len(flat)

    return {
        "log_id": new_log_id,
        "source_ocel_id": ocel_id,
        "object_type": object_type,
        "num_cases": num_cases,
        "num_events": num_events,
    }


@mcp.tool()
def export_ocel(ocel_id: str, format: str, path: str) -> dict[str, Any]:
    """Write an OCEL from the registry to disk.

    ``format`` must be one of ``"jsonocel"``, ``"xmlocel"``, ``"sqlite"``. If
    ``path`` has no directory component, the file lands in the workspace;
    otherwise the given path (absolute or relative to CWD) is used verbatim.
    """
    fmt = format.lower().lstrip(".")
    if fmt not in _OCEL_WRITE_FORMATS:
        raise UnsupportedFormat(
            f"Unsupported OCEL write format {fmt!r}. Expected one of {_OCEL_WRITE_FORMATS}."
        )

    _, ocel_obj = registry.get(ocel_id, expected_kind="ocel")
    ocel = cast(OCEL, ocel_obj)

    p = Path(path).expanduser()
    out = ensure_workspace() / p if len(p.parts) == 1 else p.resolve()

    # Ensure extension matches format (xmlocel and jsonocel are the canonical extensions).
    expected_ext = f".{fmt}"
    if out.suffix.lower() != expected_ext:
        out = out.with_suffix(expected_ext)

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(f"Could not create output directory {out.parent}: {exc}") from exc

    pm4py.write_ocel2(ocel, str(out))

    if not out.exists():
        raise WorkspaceError(f"Export reported success but file is missing: {out}")

    return OcelExportResult(
        path=str(out),
        format=fmt,
        size_bytes=out.stat().st_size,
    ).as_dict()


__all__ = [
    "describe_ocel",
    "export_ocel",
    "flatten_ocel",
    "load_ocel",
]
