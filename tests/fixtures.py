"""Shared test fixtures for pm4py-mcp.

Kept deliberately small so full-matrix CI stays fast. A 3-case, 10-event log
exercises variant counting, start/end activity detection, and duration stats
without loading a real BPI-Challenge-sized file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pm4py


def tiny_log() -> pd.DataFrame:
    """Return a 3-case, 11-event synthetic log, pm4py-formatted.

    Structure:
      - 3 cases
      - 4 unique activities: register, triage, treat, discharge
      - 2 variants:
          (register, triage, treat, discharge) x2   — cases 1, 2 (happy path)
          (register, triage, treat)              x1 — case 3 (ends before discharge)
      - end activities: discharge x2, treat x1
    """
    rows = [
        # case-1: happy path
        ("case-1", "register", "2024-01-01T08:00:00"),
        ("case-1", "triage", "2024-01-01T08:15:00"),
        ("case-1", "treat", "2024-01-01T09:00:00"),
        ("case-1", "discharge", "2024-01-01T11:30:00"),
        # case-2: happy path (same variant as case-1)
        ("case-2", "register", "2024-01-01T09:00:00"),
        ("case-2", "triage", "2024-01-01T09:20:00"),
        ("case-2", "treat", "2024-01-01T10:30:00"),
        ("case-2", "discharge", "2024-01-01T13:00:00"),
        # case-3: stops at treat — different end activity
        ("case-3", "register", "2024-01-01T10:00:00"),
        ("case-3", "triage", "2024-01-01T10:10:00"),
        ("case-3", "treat", "2024-01-01T11:00:00"),
    ]
    df = pd.DataFrame(rows, columns=["case_id", "activity", "timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return pm4py.format_dataframe(
        df,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )


def tiny_log_xes(tmp_path: Path) -> Path:
    """Write the tiny log to an XES file under ``tmp_path`` and return the path."""
    log = tiny_log()
    out = tmp_path / "tiny.xes"
    pm4py.write_xes(log, str(out))
    return out


def tiny_ocel() -> pm4py.objects.ocel.obj.OCEL:
    """Return a synthetic OCEL 2.0 with 3 object types, 10 events, 8 objects.

    Structure (same as examples/order-management.jsonocel but built in-memory):
      - 3 object types: order (2), item (4), delivery (2)
      - 10 events covering Place Order / Pick Item (x2) / Ship / Deliver per order
      - 16 event-to-object relations
    """
    from pm4py.objects.ocel.obj import OCEL

    events = pd.DataFrame(
        [
            ("e01", "Place Order", "2024-01-01T08:00:00"),
            ("e02", "Pick Item", "2024-01-01T08:30:00"),
            ("e03", "Pick Item", "2024-01-01T08:45:00"),
            ("e04", "Ship", "2024-01-01T10:00:00"),
            ("e05", "Deliver", "2024-01-01T14:00:00"),
            ("e06", "Place Order", "2024-01-01T09:00:00"),
            ("e07", "Pick Item", "2024-01-01T09:30:00"),
            ("e08", "Pick Item", "2024-01-01T09:45:00"),
            ("e09", "Ship", "2024-01-01T11:00:00"),
            ("e10", "Deliver", "2024-01-01T15:30:00"),
        ],
        columns=["ocel:eid", "ocel:activity", "ocel:timestamp"],
    )
    events["ocel:timestamp"] = pd.to_datetime(events["ocel:timestamp"], utc=True)

    objects = pd.DataFrame(
        [
            ("o1", "order"),
            ("o2", "order"),
            ("i1", "item"),
            ("i2", "item"),
            ("i3", "item"),
            ("i4", "item"),
            ("d1", "delivery"),
            ("d2", "delivery"),
        ],
        columns=["ocel:oid", "ocel:type"],
    )

    ts = events["ocel:timestamp"].tolist()
    relations = pd.DataFrame(
        [
            ("e01", "o1", "order", "Place Order", ts[0], "default"),
            ("e02", "o1", "order", "Pick Item", ts[1], "default"),
            ("e02", "i1", "item", "Pick Item", ts[1], "default"),
            ("e03", "o1", "order", "Pick Item", ts[2], "default"),
            ("e03", "i2", "item", "Pick Item", ts[2], "default"),
            ("e04", "o1", "order", "Ship", ts[3], "default"),
            ("e04", "d1", "delivery", "Ship", ts[3], "default"),
            ("e05", "d1", "delivery", "Deliver", ts[4], "default"),
            ("e06", "o2", "order", "Place Order", ts[5], "default"),
            ("e07", "o2", "order", "Pick Item", ts[6], "default"),
            ("e07", "i3", "item", "Pick Item", ts[6], "default"),
            ("e08", "o2", "order", "Pick Item", ts[7], "default"),
            ("e08", "i4", "item", "Pick Item", ts[7], "default"),
            ("e09", "o2", "order", "Ship", ts[8], "default"),
            ("e09", "d2", "delivery", "Ship", ts[8], "default"),
            ("e10", "d2", "delivery", "Deliver", ts[9], "default"),
        ],
        columns=[
            "ocel:eid",
            "ocel:oid",
            "ocel:type",
            "ocel:activity",
            "ocel:timestamp",
            "ocel:qualifier",
        ],
    )

    return OCEL(events=events, objects=objects, relations=relations)


def tiny_ocel_file(tmp_path: Path) -> Path:
    """Write the tiny OCEL as a JSON-OCEL file under ``tmp_path`` and return the path."""
    ocel = tiny_ocel()
    out = tmp_path / "tiny.jsonocel"
    pm4py.write_ocel2(ocel, str(out))
    return out


def tiny_petri_net() -> tuple:  # type: ignore[type-arg]
    """Discover a Petri net from ``tiny_log()`` via the Inductive Miner.

    Returns ``(net, initial_marking, final_marking)`` — the shape Phase 1
    stores under a ``petri_net`` kind handle. Tests that need a ``petri_id``
    should call this and put the tuple into the registry themselves.
    """
    return pm4py.discover_petri_net_inductive(tiny_log())
