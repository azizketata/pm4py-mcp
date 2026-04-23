"""Timestamp normalization shared across tools.

Extracted from ``tools/filters.py`` in Phase 2 Slice 1 so both the traditional
``filter_time_range`` and the OCEL ``filter_ocel_time_range`` can reuse it.
PM4Py's filter implementations parse datetime strings with the format
``'%Y-%m-%d %H:%M:%S'`` — they do not accept the ISO-8601 ``T`` separator,
so we round-trip through pandas.
"""

from __future__ import annotations

import pandas as pd


def normalize_datetime(value: str) -> str:
    """Convert any pandas-parseable datetime string to pm4py's expected format.

    pm4py's ``filter_time_range`` / ``filter_ocel_events_timestamp`` internally
    call ``datetime.strptime(value, '%Y-%m-%d %H:%M:%S')`` — no ``T`` separator,
    no microseconds. ``pd.to_datetime`` happily accepts either form, so we
    round-trip through it to normalize.
    """
    return str(pd.to_datetime(value).strftime("%Y-%m-%d %H:%M:%S"))
