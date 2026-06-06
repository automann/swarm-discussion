#!/usr/bin/env python3
"""
Fan-in demux for swarm-discussion native subagents.

The runtime returns `multi_agent_v1.wait_agent` results keyed by `agent_id` (NOT persona name). Native shape:

    { "status": { "<agent_id>": { "completed": "<JSON string>" } }, "timed_out": false }

The orchestrator records the spawn-time `agent_id -> persona` map (it knows which agent_id it got for which
persona). `demux` returns the parsed results in **deterministic spawn order** so `wal.py` mints ids
deterministically (never by arrival order). If an agent_id is missing from the map, it falls back to matching
the payload's `name`/`token`.

CLI:
  collect.py --spawn-order '[{"agentId":"…","persona":"…","token":"…"}, …]'  < wait_result.json
    -> { "results": [{"persona","agentId","result"}, …], "errors": [...], "timedOut": bool }

Importable: demux(wait_result, spawn_order). Exit 0 if no errors and not timed out, else 1.
"""
import argparse, json, sys


def _payload(entry):
    """Parse the JSON string under `.completed`; return (obj, error_or_None)."""
    if not isinstance(entry, dict):
        return None, "status entry is not an object"
    if "completed" not in entry:
        return None, f"agent did not complete (status keys: {sorted(entry)})"
    raw = entry["completed"]
    if isinstance(raw, dict):
        return raw, None
    try:
        return json.loads(raw), None
    except (TypeError, json.JSONDecodeError) as e:
        return None, f"unparseable .completed payload: {e}"


def demux(wait_result, spawn_order):
    """Map a wait_agent result to persona-keyed results in spawn order."""
    wait_result = wait_result or {}
    status = wait_result.get("status") or {}
    timed_out = bool(wait_result.get("timed_out"))
    parsed = {aid: _payload(e)[0] for aid, e in status.items()}   # for name/token fallback
    results, errors = [], []
    for spec in spawn_order:
        aid = spec.get("agentId") or spec.get("agent_id")
        persona = spec.get("persona")
        entry = status.get(aid)
        if entry is None:                                          # fallback: match payload name/token
            match = next((a for a, p in parsed.items()
                          if p and (p.get("name") == persona or
                                    (spec.get("token") and p.get("token") == spec.get("token")))), None)
            if match is None:
                errors.append({"persona": persona, "agentId": aid,
                               "error": "no result for agent_id and no name/token fallback match"})
                continue
            aid, entry = match, status[match]
        obj, err = _payload(entry)
        if err:
            errors.append({"persona": persona, "agentId": aid, "error": err})
            continue
        results.append({"persona": persona, "agentId": aid, "result": obj})
    return {"results": results, "errors": errors, "timedOut": timed_out}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spawn-order", required=True, help="JSON list of {agentId, persona, token?} in spawn order")
    a = p.parse_args()
    out = demux(json.load(sys.stdin), json.loads(a.spawn_order))
    print(json.dumps(out, indent=2))
    sys.exit(0 if (not out["errors"] and not out["timedOut"]) else 1)


if __name__ == "__main__":
    main()
