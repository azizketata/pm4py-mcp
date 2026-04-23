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
