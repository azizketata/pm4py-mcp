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
    """Return a 3-case, 10-event synthetic log, pm4py-formatted.

    Structure:
      - 3 cases
      - 4 unique activities: register, triage, treat, discharge
      - 2 variants: (register, triage, treat, discharge) x2; (register, triage, discharge) x1
    """
    rows = [
        ("case-1", "register", "2024-01-01T08:00:00"),
        ("case-1", "triage", "2024-01-01T08:15:00"),
        ("case-1", "treat", "2024-01-01T09:00:00"),
        ("case-1", "discharge", "2024-01-01T11:30:00"),
        ("case-2", "register", "2024-01-01T09:00:00"),
        ("case-2", "triage", "2024-01-01T09:20:00"),
        ("case-2", "discharge", "2024-01-01T09:45:00"),
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
