"""Phase 2 Part 2 (0.4.1) — model simulation.

Wraps ``pm4py.play_out`` so a discovered model can be replayed as a fresh
simulated event log. The returned ``log_id`` is a regular ``"log"`` kind,
so the output composes with every Phase 1 tool (``describe_log``,
``abstract_variants``, ``conformance_*``, filters, etc.).

Registry lineage: the simulated log's ``source_handle`` points at the
model that produced it, so chained workflows stay debuggable.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import pm4py

from pm4py_mcp.errors import InvalidKind
from pm4py_mcp.server import mcp, registry

# pm4py's internal parameter name for trace count differs per playout variant.
_NO_TRACES_PARAM_PETRI = "noTraces"
_NO_TRACES_PARAM_TREE = "num_traces"
# Cap to protect against runaway playouts on cyclic models.
_MAX_NUM_TRACES = 10_000


def _backfill_tree_playout_attributes(event_log: Any) -> Any:
    """Process-tree playout produces Trace objects with no concept:name and
    no timestamps. Inject synthetic values so convert_to_dataframe yields a
    proper ``case:concept:name`` + ``time:timestamp`` column layout that
    composes with Phase 1 tools.
    """
    base = _dt.datetime(2024, 1, 1, tzinfo=_dt.timezone.utc)
    for i, trace in enumerate(event_log):
        trace.attributes["concept:name"] = f"sim-case-{i}"
        for j, event in enumerate(trace):
            if "time:timestamp" not in event:
                event["time:timestamp"] = base + _dt.timedelta(minutes=i * 60 + j)
    return event_log


@mcp.tool()
def simulate_log(model_id: str, num_traces: int = 1000) -> dict[str, Any]:
    """Simulate an event log by replaying a discovered model.

    Accepts Petri net (tuple) or process tree handles. BPMN and POWL are NOT
    supported by ``pm4py.play_out`` directly — convert them first via
    ``convert_model(bpmn_id, target_kind="petri_net")``.

    The returned ``log_id`` is a regular ``"log"`` kind, so the simulated log
    composes with every Phase 1 tool. ``source_handle`` points at the source
    model for lineage.

    ``num_traces`` is capped at 10_000 to protect against runaway generation
    on cyclic models.
    """
    if num_traces < 1:
        raise ValueError(f"num_traces must be >= 1, got {num_traces}")
    if num_traces > _MAX_NUM_TRACES:
        raise ValueError(
            f"num_traces {num_traces} exceeds safety cap of {_MAX_NUM_TRACES}. "
            "Simulation of cyclic models can produce unbounded output; raise the "
            "cap only if you've checked the model's reachability."
        )

    kind, payload = registry.get(model_id)
    if kind not in ("petri_net", "process_tree"):
        raise InvalidKind(
            f"simulate_log requires a petri_net or process_tree handle; got {kind!r}. "
            f"If you have a bpmn/powl model, use "
            f"convert_model({model_id!r}, target_kind='petri_net') first."
        )

    # Petri nets are stored as (net, im, fm) tuples; unpack for pm4py.play_out.
    args = tuple(payload) if kind == "petri_net" else (payload,)
    # Petri playout and tree playout use DIFFERENT parameter-name conventions
    # for trace count (pm4py internal — "noTraces" vs "num_traces"). Pass both
    # to be robust; pm4py's variant-specific code reads whichever matches.
    parameters = {
        _NO_TRACES_PARAM_PETRI: num_traces,
        _NO_TRACES_PARAM_TREE: num_traces,
    }
    simulated = pm4py.play_out(*args, parameters=parameters)

    if kind == "process_tree":
        # Tree playout leaves trace.attributes empty and events timestampless;
        # inject synthetic case_ids + timestamps so the DataFrame conversion
        # yields the columns Phase 1 tools expect.
        simulated = _backfill_tree_playout_attributes(simulated)

    # pm4py.play_out returns a legacy EventLog. Convert to DataFrame so the
    # simulated log composes with every Phase 1 tool that expects DataFrame
    # input (describe_log, abstract_variants, ...).
    df = pm4py.convert_to_dataframe(simulated)

    log_id = registry.put("log", df, source_handle=model_id)
    return {
        "log_id": log_id,
        "source_model_id": model_id,
        "source_kind": kind,
        "num_traces_requested": num_traces,
        "num_traces_produced": int(df["case:concept:name"].nunique()),
        "num_events": int(len(df)),
    }


__all__ = ["simulate_log"]
