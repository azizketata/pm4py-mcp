"""Typed return-value shapes for tool handlers.

Kept deliberately light — plain dataclasses with an ``as_dict`` convenience.
FastMCP serializes via ``pydantic_core.to_json(..., fallback=str)`` so almost
anything JSON-compatible works, but structured types give mypy something
to check and document the contract explicitly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LogSummary:
    """Compact summary of an event log, safe to return from a tool response.

    Capped in size so it stays under the ~1 MB Claude Desktop response
    ceiling even on huge logs. Returned by ``load_event_log`` and
    ``describe_log``.
    """

    log_id: str
    num_cases: int
    num_events: int
    num_activities: int
    activities_preview: list[str]  # capped to 20 alphabetically
    time_range: tuple[str, str]  # ISO-8601 strings
    top_variants: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExportResult:
    """Returned by ``export_log`` — the absolute output path and size."""

    path: str
    format: str
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkspaceEntry:
    """One entry returned by ``list_workspace``."""

    name: str
    path: str
    size_bytes: int
    modified: str  # ISO-8601

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OcelSummary:
    """Compact summary of an OCEL 2.0 event log.

    Returned by ``load_ocel`` and ``describe_ocel``. Caps previews so a
    BPI-Challenge-sized OCEL still fits under Claude Desktop's response ceiling.
    """

    ocel_id: str
    num_events: int
    num_objects: int
    num_object_types: int
    object_types: list[str]  # capped to 20, alphabetical
    events_per_object_type: dict[str, int]  # top 10 by count
    num_activities: int
    activities_preview: list[str]  # capped to 20, alphabetical
    time_range: tuple[str, str]  # ISO-8601 strings

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OcelExportResult:
    """Returned by ``export_ocel`` — output path, format, size."""

    path: str
    format: str  # "jsonocel" | "xmlocel" | "sqlite"
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FilterResult:
    """Returned by every ``filter_*`` tool.

    Filters never mutate the source log — each call mints a fresh handle
    so the user can keep references to intermediate states.
    """

    new_log_id: str
    source_log_id: str
    filter: str
    num_cases_before: int
    num_cases_after: int
    num_events_before: int
    num_events_after: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConformanceResult:
    """Returned by ``conformance_token_replay`` and ``conformance_alignments``.

    Only aggregate stats — never the per-trace list, which can be 100k+ rows
    on a real log and blow Claude Desktop's 1 MB response cap.
    """

    log_id: str
    petri_id: str
    algorithm: str  # "token_replay" | "alignments"
    num_cases: int
    num_fit_cases: int
    mean_trace_fitness: float  # 0.0 .. 1.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
