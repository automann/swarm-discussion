#!/usr/bin/env python3
"""
Context windowing for swarm-discussion.

`sliceForPersona` is a STATELESS PROJECTION of the canonical log into what one persona may cite this step.
Pure data -> text — no runtime calls.

Invariants:
  - NEVER window a persona's own history — its messages are always full (identity spine).
  - Fixed-role framing (moderator / contrarian / cross-domain) is always full (pinned).
  - Peer (other dynamic experts') bodies are windowed newest-first to a char budget; elided peers keep
    "[id] from (type): <gist ≤120 chars>  (elided)" so message IDs are NEVER dropped.
  - Anti-anchoring (no peer content at the declaration phase) is enforced by PROTOCOL.md; defensively this
    returns an empty slice for phase == "position_declaration".

Returns: {"sliceText", "injectedIds", "visibility"} where
  - injectedIds: every id rendered in the slice (full OR gist), in order — "what ids appear".
  - visibility:  {id: "full" | "gist"} — the load-bearing distinction for provenance. The orchestrator
    persists THIS (not bare injectedIds) into `partial.personaContextLog[persona]`.

`provenance` guards the principal residual risk: a recorded positionShift whose trigger id the persona was
never shown IN FULL (absent, or only gisted) — re-hydration amnesia / hallucinated citation. A shift with no
trigger id at all is also a violation (the response must name what moved it).

CLI:
  window.py slice --persona ID --phase P [--budget N]   < {"messages":[...]}  -> {sliceText, injectedIds, visibility}
  window.py provenance   < {"positionShifts":[...], "personaContextLog":{persona: <ids list | {id:vis}>}}  -> {"violations":[...]}
"""
import argparse, json, sys

FIXED = {"moderator", "historian", "contrarian", "cross-domain"}
GIST = 120


def _text(m):
    t = m.get("text")
    if isinstance(t, str) and t:
        return t
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        for k in ("position", "challenge", "response", "analogy", "summary", "reasoning", "targetConsensus"):
            if c.get(k):
                return str(c[k])
        return json.dumps(c)[:300]
    return ""


def _full(m):
    return f"[{m['id']}] {m.get('from', '?')} ({m.get('type', '?')}): {_text(m)}"


def _gist(m):
    t = _text(m)
    t = t if len(t) <= GIST else t[:GIST - 1] + "…"          # body length stays <= GIST (marker included)
    return f"[{m['id']}] {m.get('from', '?')} ({m.get('type', '?')}): {t}  (elided)"


def slice_for_persona(messages, persona, phase, budget=100000, fixed=FIXED):
    if phase == "position_declaration":
        return {"sliceText": "", "injectedIds": [], "visibility": {}}   # anti-anchoring
    peers = [m for m in messages if m.get("from") != persona and m.get("from") not in fixed]
    full_peer, used = set(), 0
    for m in reversed(peers):                                 # keep NEWEST peers in full first
        line = _full(m)
        if used + len(line) <= budget:
            full_peer.add(m["id"])
            used += len(line)
    lines, injected, visibility = [], [], {}
    for m in messages:                                        # render chronologically
        injected.append(m["id"])
        frm = m.get("from")
        full = frm == persona or frm in fixed or m["id"] in full_peer
        lines.append(_full(m) if full else _gist(m))
        visibility[m["id"]] = "full" if full else "gist"
    return {"sliceText": "\n".join(lines), "injectedIds": injected, "visibility": visibility}


def _trigger_ids(shift):
    """Real trigger ids the response named. Accepts `triggerIds`/`shiftTriggerIds`/`trigger`, each of which
    may be a LIST (the PROTOCOL/SCHEMA position-shift shape) or a single id STRING. Returns [] when none were
    provided (itself a violation). NB: `trigger` is an array in the protocol — must not be wrapped again."""
    for key in ("triggerIds", "shiftTriggerIds", "trigger"):
        v = shift.get(key)
        if isinstance(v, list):
            return [t for t in v if t]
        if isinstance(v, str) and v:
            return [v]
    return []


def provenance(position_shifts, persona_context_log):
    """A shift is sound iff it names >=1 trigger id and every trigger was shown to that persona IN FULL.
    persona_context_log[expert] may be a list of ids (legacy: all treated full) or {id: 'full'|'gist'}."""
    violations = []
    for s in position_shifts:
        exp = s.get("expert")
        ctx = persona_context_log.get(exp, [])
        seen_full = set(ctx) if isinstance(ctx, list) else {i for i, v in ctx.items() if v == "full"}
        present = set(ctx) if isinstance(ctx, list) else set(ctx.keys())
        tids = _trigger_ids(s)
        if not tids:
            violations.append({"expert": exp, "trigger": None,
                               "reason": "position shift names no trigger id (the response must cite what moved it)"})
            continue
        for tid in tids:
            if tid not in present:
                violations.append({"expert": exp, "trigger": tid,
                                   "reason": "shift cites an id the persona was never shown (absent / hallucinated)"})
            elif tid not in seen_full:
                violations.append({"expert": exp, "trigger": tid,
                                   "reason": "shift cites an id the persona saw only as a gist, not in full"})
    return {"violations": violations}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("slice")
    s.add_argument("--persona", required=True)
    s.add_argument("--phase", required=True)
    s.add_argument("--budget", type=int, default=100000)
    sub.add_parser("provenance")
    a = p.parse_args()
    data = json.load(sys.stdin)
    if a.cmd == "slice":
        print(json.dumps(slice_for_persona(data["messages"], a.persona, a.phase, a.budget)))
    else:
        print(json.dumps(provenance(data.get("positionShifts", []), data.get("personaContextLog", {}))))


if __name__ == "__main__":
    main()
