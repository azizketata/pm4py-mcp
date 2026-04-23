"""Generate the bundled order-management example OCEL.

Produces ``examples/order-management.jsonocel``: a tiny synthetic object-centric
event log with 3 object types (``order``, ``item``, ``delivery``) and ~10 events
across 2 orders. Small enough that full-matrix CI stays fast; rich enough to
exercise the OCEL flatten bridge, object-centric DFG/PetriNet discovery, and
every OCEL filter strategy.

Re-run this script whenever the fixture shape changes — the output file is
committed to the repo so no generation step runs at install time.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.ocel.obj import OCEL

OUT = Path(__file__).resolve().parent.parent / "examples" / "order-management.jsonocel"


def _build_ocel() -> OCEL:
    """Return a synthetic 2-order, 4-item, 2-delivery OCEL.

    Structure (all timestamps 2024-01-01 in UTC):

    - order-1 (o1): Place Order -> Pick Item (i1) -> Pick Item (i2) -> Ship -> Deliver (d1)
    - order-2 (o2): Place Order -> Pick Item (i3) -> Pick Item (i4) -> Ship -> Deliver (d2)

    Every event touches at least one object. The two orders share the same
    happy-path variant after flattening on object_type='order', so
    `discover_petri_net` on the flattened log produces a clean sequence.
    """
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

    # Relations: which event touches which object (with a free-form qualifier).
    # The qualifier is required for OCEL 2.0; "default" is fine for this fixture.
    relations = pd.DataFrame(
        [
            # order-1 trail
            ("e01", "o1", "order", "Place Order", events.iloc[0]["ocel:timestamp"], "default"),
            ("e02", "o1", "order", "Pick Item", events.iloc[1]["ocel:timestamp"], "default"),
            ("e02", "i1", "item", "Pick Item", events.iloc[1]["ocel:timestamp"], "default"),
            ("e03", "o1", "order", "Pick Item", events.iloc[2]["ocel:timestamp"], "default"),
            ("e03", "i2", "item", "Pick Item", events.iloc[2]["ocel:timestamp"], "default"),
            ("e04", "o1", "order", "Ship", events.iloc[3]["ocel:timestamp"], "default"),
            ("e04", "d1", "delivery", "Ship", events.iloc[3]["ocel:timestamp"], "default"),
            ("e05", "d1", "delivery", "Deliver", events.iloc[4]["ocel:timestamp"], "default"),
            # order-2 trail
            ("e06", "o2", "order", "Place Order", events.iloc[5]["ocel:timestamp"], "default"),
            ("e07", "o2", "order", "Pick Item", events.iloc[6]["ocel:timestamp"], "default"),
            ("e07", "i3", "item", "Pick Item", events.iloc[6]["ocel:timestamp"], "default"),
            ("e08", "o2", "order", "Pick Item", events.iloc[7]["ocel:timestamp"], "default"),
            ("e08", "i4", "item", "Pick Item", events.iloc[7]["ocel:timestamp"], "default"),
            ("e09", "o2", "order", "Ship", events.iloc[8]["ocel:timestamp"], "default"),
            ("e09", "d2", "delivery", "Ship", events.iloc[8]["ocel:timestamp"], "default"),
            ("e10", "d2", "delivery", "Deliver", events.iloc[9]["ocel:timestamp"], "default"),
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


def main() -> None:
    ocel = _build_ocel()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pm4py.write_ocel2(ocel, str(OUT))
    size = OUT.stat().st_size
    print(
        f"wrote {OUT} ({size:,} bytes, "
        f"{len(ocel.events)} events, {len(ocel.objects)} objects, "
        f"{len(ocel.relations)} relations)"
    )


if __name__ == "__main__":
    main()
