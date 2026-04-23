"""Regenerate ``examples/running-example.xes`` from an in-repo fixture.

Run from the repo root:

    uv run python scripts/generate_example_log.py

The output is a small hospital-workflow log — a handful of cases exhibiting
two variants (happy path + early exit). It is used by:

- The README's walking-example session.
- Phase 1's manual Claude Desktop smoke test.
- The Inspector nightly CI check (loaded once to exercise load_event_log).

Why a hand-rolled log and not a BPI Challenge dataset? Committing real
challenge logs would bloat the repo to hundreds of MB. Phase 4 of the
roadmap ships ``scripts/download_benchmark_logs.py`` for those.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pm4py

OUT = Path(__file__).resolve().parent.parent / "examples" / "running-example.xes"


def _build_log() -> pd.DataFrame:
    """8 cases, 2 variants, 5 activities — fits on one screen as a DFG."""
    rows = [
        # case-1 .. case-6: happy path (register, triage, treat, discharge)
        ("case-1", "register", "2024-01-01T08:00:00"),
        ("case-1", "triage", "2024-01-01T08:15:00"),
        ("case-1", "treat", "2024-01-01T09:00:00"),
        ("case-1", "discharge", "2024-01-01T11:30:00"),
        ("case-2", "register", "2024-01-01T09:00:00"),
        ("case-2", "triage", "2024-01-01T09:20:00"),
        ("case-2", "treat", "2024-01-01T10:30:00"),
        ("case-2", "discharge", "2024-01-01T13:00:00"),
        ("case-3", "register", "2024-01-01T09:30:00"),
        ("case-3", "triage", "2024-01-01T09:45:00"),
        ("case-3", "treat", "2024-01-01T10:45:00"),
        ("case-3", "discharge", "2024-01-01T12:15:00"),
        ("case-4", "register", "2024-01-01T10:05:00"),
        ("case-4", "triage", "2024-01-01T10:25:00"),
        ("case-4", "treat", "2024-01-01T11:40:00"),
        ("case-4", "discharge", "2024-01-01T14:00:00"),
        ("case-5", "register", "2024-01-01T11:00:00"),
        ("case-5", "triage", "2024-01-01T11:15:00"),
        ("case-5", "treat", "2024-01-01T12:30:00"),
        ("case-5", "discharge", "2024-01-01T15:15:00"),
        ("case-6", "register", "2024-01-01T12:15:00"),
        ("case-6", "triage", "2024-01-01T12:35:00"),
        ("case-6", "treat", "2024-01-01T13:45:00"),
        ("case-6", "discharge", "2024-01-01T16:00:00"),
        # case-7, case-8: register -> triage -> consult -> discharge (second variant)
        ("case-7", "register", "2024-01-01T13:00:00"),
        ("case-7", "triage", "2024-01-01T13:20:00"),
        ("case-7", "consult", "2024-01-01T14:00:00"),
        ("case-7", "discharge", "2024-01-01T15:30:00"),
        ("case-8", "register", "2024-01-01T14:00:00"),
        ("case-8", "triage", "2024-01-01T14:15:00"),
        ("case-8", "consult", "2024-01-01T14:45:00"),
        ("case-8", "discharge", "2024-01-01T16:30:00"),
    ]
    df = pd.DataFrame(rows, columns=["case_id", "activity", "timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return pm4py.format_dataframe(
        df,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )


def main() -> None:
    log = _build_log()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pm4py.write_xes(log, str(OUT))
    size = OUT.stat().st_size
    print(
        f"wrote {OUT} ({size:,} bytes, {len(log)} events, {log['case:concept:name'].nunique()} cases)"
    )


if __name__ == "__main__":
    main()
