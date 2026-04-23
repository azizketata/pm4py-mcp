"""Handle-based in-memory artifact registry.

Tools exchange short opaque handles (e.g. ``log-ab3x7k``) rather than event
logs or DataFrames — event logs can be 10 MB to 1 GB and Claude Desktop
enforces a ~1 MB response cap.

Eviction policy: least-recently-used past capacity, and TTL-based expiry
on every access. Both are configurable at construction; defaults come from
``CLAUDE.md`` (capacity 8, TTL 3600s).

State does not persist across client restarts — there is no disk cache.
Workspace files on disk are the only durable output.
"""

from __future__ import annotations

import base64
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal

from pm4py_mcp.errors import HandleNotFound, InvalidKind

Kind = Literal["log", "petri_net", "process_tree", "bpmn", "dfg", "ocel", "ocdfg", "ocpn"]

_PREFIX: dict[Kind, str] = {
    "log": "log",
    "petri_net": "pn",
    "process_tree": "pt",
    "bpmn": "bpmn",
    "dfg": "dfg",
    "ocel": "ocel",
    "ocdfg": "ocdfg",
    "ocpn": "ocpn",
}


@dataclass
class _Entry:
    kind: Kind
    payload: Any
    inserted_at: float


class LogRegistry:
    """LRU + TTL artifact store keyed by short handles."""

    def __init__(self, *, capacity: int = 8, ttl_seconds: float = 3600.0) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        self._capacity = capacity
        self._ttl = ttl_seconds
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    def put(self, kind: Kind, payload: Any) -> str:
        """Store an artifact and return its freshly minted handle."""
        if kind not in _PREFIX:
            raise InvalidKind(f"Unknown kind {kind!r}; expected one of {list(_PREFIX)}")
        self._evict_expired()
        handle = self._mint_handle(kind)
        self._entries[handle] = _Entry(kind=kind, payload=payload, inserted_at=self._now())
        self._evict_to_capacity()
        return handle

    def get(self, handle: str, *, expected_kind: Kind | None = None) -> tuple[Kind, Any]:
        """Return ``(kind, payload)`` for a handle, touching it as the most recent.

        Raises
        ------
        HandleNotFound
            Handle never existed or its TTL expired.
        InvalidKind
            ``expected_kind`` was given and does not match the stored kind.
        """
        self._evict_expired()
        if handle not in self._entries:
            raise HandleNotFound(
                f"No artifact for handle {handle!r}. "
                "It may have expired (1h TTL) or never existed in this server session."
            )
        self._entries.move_to_end(handle)
        entry = self._entries[handle]
        if expected_kind is not None and entry.kind != expected_kind:
            raise InvalidKind(
                f"Handle {handle!r} is a {entry.kind}; this tool expects a {expected_kind}."
            )
        return entry.kind, entry.payload

    def __contains__(self, handle: object) -> bool:
        if not isinstance(handle, str):
            return False
        self._evict_expired()
        return handle in self._entries

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._entries)

    def keys(self) -> list[str]:
        """Return currently live handles, most-recently-used last."""
        self._evict_expired()
        return list(self._entries.keys())

    def clear(self) -> None:
        self._entries.clear()

    # --- hooks for testing ---

    def _now(self) -> float:
        return time.monotonic()

    # --- internals ---

    def _mint_handle(self, kind: Kind) -> str:
        # 4 random bytes -> 7-char lowercase base32 (no padding), e.g. "ab3x7kq"
        raw = base64.b32encode(uuid.uuid4().bytes[:4]).decode("ascii")
        suffix = raw.rstrip("=").lower()
        return f"{_PREFIX[kind]}-{suffix}"

    def _evict_expired(self) -> None:
        now = self._now()
        expired = [h for h, e in self._entries.items() if now - e.inserted_at > self._ttl]
        for h in expired:
            del self._entries[h]

    def _evict_to_capacity(self) -> None:
        while len(self._entries) > self._capacity:
            self._entries.popitem(last=False)
