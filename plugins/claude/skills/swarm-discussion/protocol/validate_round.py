#!/usr/bin/env python3
"""
Validate a COMMITTED round record (`rounds/{NNN}.json`) against the SCHEMA invariants.

This is a self-consistency check only; no ground truth is needed.

Checks: round-record fields present; message-id grammar / gapless / unique / round-matched; argument-graph
edges + message references resolve to present ids; `synthesis` present (the B3 flush-then-commit fix);
metadata consistency; and — if `personaContextLog` was retained — shift provenance (each shift's trigger ids
were shown to that persona IN FULL).

Usage: validate_round.py <path/to/rounds/NNN.json>   ->  PASS/FAIL per check; exit 0 ok / 1 fail.
"""
import argparse, json, sys

import re
ID = re.compile(r"^r(\d+)-msg-(\d{3})$")


def validate(d):
    fails = []
    def chk(cond, msg):
        print(("PASS " if cond else "FAIL ") + msg)
        if not cond:
            fails.append(msg)

    for f in ("roundId", "topic", "mode", "timestamp", "messages", "argumentGraph",
              "positionShifts", "synthesis", "metadata"):
        chk(f in d, f"round-record field present: {f}")

    msgs = d.get("messages", []) or []
    ids = [m.get("id") for m in msgs]
    rnd = d.get("roundId")
    seqs = []
    for i in ids:
        m = ID.match(i or "")
        chk(bool(m), f"message-id grammar: {i!r}")
        if m:
            chk(int(m.group(1)) == rnd, f"id round matches roundId ({rnd}): {i}")
            seqs.append(int(m.group(2)))
    chk(len(ids) == len(set(ids)), "message ids unique")
    chk(sorted(seqs) == list(range(1, len(seqs) + 1)), f"message ids gapless 1..{len(seqs)} (got {sorted(seqs)})")

    present = set(ids)
    for e in d.get("argumentGraph", []) or []:
        chk(e.get("from") in present and e.get("to") in present,
            f"argument-graph edge resolves: {e.get('from')} -> {e.get('to')}")
    for m in msgs:
        for r in (m.get("references") or []):
            chk(r.get("targetId") in present, f"reference resolves: {m.get('id')} -> {r.get('targetId')}")

    chk(bool(d.get("synthesis")), "synthesis present (committed round — B3 flush-then-commit)")

    md = d.get("metadata", {}) or {}
    chk(md.get("messageCount") == len(msgs), f"metadata.messageCount == {len(msgs)}")
    chk(md.get("referenceCount") == len(d.get("argumentGraph", []) or []), "metadata.referenceCount == len(argumentGraph)")
    chk(set(md.get("participants") or []) == {m.get("from") for m in msgs}, "metadata.participants == distinct message senders")

    pcl = d.get("personaContextLog")
    if pcl:
        for s in d.get("positionShifts", []) or []:
            trig = s.get("trigger")
            tids = trig if isinstance(trig, list) else ([trig] if trig else [])
            vis = pcl.get(s.get("expert"), {}) or {}
            shown_full = (lambda t: vis.get(t) == "full") if isinstance(vis, dict) else (lambda t: t in vis)
            for t in tids:
                chk(shown_full(t), f"provenance: shift by {s.get('expert')} cites id shown in full: {t}")
    else:
        print("note  personaContextLog not retained at commit — provenance check skipped (allowed by SCHEMA)")
    return fails


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round_path", help="Path to a committed rounds/NNN.json record")
    args = parser.parse_args()
    fails = validate(json.load(open(args.round_path)))
    print("\nALL PASS" if not fails else f"\n{len(fails)} FAILURE(S)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
