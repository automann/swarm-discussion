#!/usr/bin/env python3
"""
Write-ahead log for swarm-discussion durability.

The `rounds/{NNN}.json.partial` file is the SYSTEM OF RECORD; the orchestrator's in-context state is a
cache. The runtime calls this through the `checkpoint` seam method. See protocol/durability.md.

Guarantees:
  - atomic flush          : write `.tmp`, fsync file, os.replace -> `.partial`, fsync parent dir
  - durable monotonic IDs : ids derive from the max seq in the round STATE files (.partial/.json) only,
                            never from progress.md, so a stray informational log can't advance the counter
  - resume-from-partial   : choose the HIGHEST round across partials+finals; prefer the partial only when
                            the top round has one (a stale lower-round partial never wins)
  - collision guard       : a minted id is never one already present in the round state

CLI (used by the orchestrator):
  wal.py flush   --dir D --round N --phase P   <state.json on stdin>   # atomic per-step flush
  wal.py commit  --dir D --round N                                     # promote .partial -> .json (fsync'd)
  wal.py max-seq --dir D --round N                                     # highest seq in round state (seed the counter)
  wal.py next-id --dir D --round N                                     # max-seq+1, collision-guarded -> "rN-msg-nnn"
  wal.py resume  --dir D                                               # {round, phase, maxId, source: partial|final|none}
  wal.py load    --dir D --round N                                     # current .partial (else .json) state JSON

Importable: max_seq(), mint_next_id(), flush(), commit(), resume_point(), load_state(), valid_discussion_id().
Exit 0 ok, 2 usage.
"""
import argparse, json, os, re, sys
from pathlib import Path

_ID = re.compile(r"r(\d+)-msg-(\d{3})")
# A discussion id is a single slug segment — no separators, no traversal (M6 containment).
_DISCUSSION_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")


def valid_discussion_id(s):
    """True iff `s` is a safe single-segment discussion id (runtimes must check before building paths)."""
    return bool(_DISCUSSION_ID.fullmatch(s or "")) and ".." not in s


def _paths(d, rnd):
    rd = Path(d) / "rounds"
    n = f"{int(rnd):03d}"
    return rd, rd / f"{n}.json", rd / f"{n}.json.partial", rd / f"{n}.json.tmp", Path(d) / "progress.md"


def _fsync_dir(path):
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, ValueError):
        pass  # not all platforms/dirs support dir fsync; best-effort durability


def _seqs_on_disk(d, rnd):
    """Seqs for `rnd` from the round STATE files only (.partial + .json) — NOT progress.md."""
    _rd, final, partial, _tmp, _progress = _paths(d, rnd)
    seqs = set()
    for p in (partial, final):
        if p.exists():
            for m in json.loads(p.read_text()).get("messages", []):
                mt = _ID.fullmatch(m.get("id", ""))
                if mt and int(mt.group(1)) == int(rnd):
                    seqs.add(int(mt.group(2)))
    return seqs


def max_seq(d, rnd):
    seqs = _seqs_on_disk(d, rnd)
    return max(seqs) if seqs else 0


def mint_next_id(d, rnd):
    seqs = _seqs_on_disk(d, rnd)
    n = (max(seqs) if seqs else 0) + 1
    while n in seqs:                      # collision guard (defensive)
        n += 1
    return f"r{int(rnd)}-msg-{n:03d}"


def flush(d, rnd, phase, state):
    rd, _final, partial, tmp, progress = _paths(d, rnd)
    rd.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state["round"], state["phase"] = int(rnd), phase
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, partial)             # atomic
    _fsync_dir(rd)
    # progress.md is an APPEND-ONLY informational id log (never an authoritative id source).
    seen = set(_ID.findall(progress.read_text())) if progress.exists() else set()
    new = [m["id"] for m in state.get("messages", [])
           if (mt := _ID.fullmatch(m.get("id", ""))) and (mt.group(1), mt.group(2)) not in seen]
    if new:
        with open(progress, "a") as f:
            for i in new:
                f.write(f"{i} emitted\n")
            f.flush()
            os.fsync(f.fileno())
    return str(partial)


def commit(d, rnd):
    rd, final, partial, _tmp, _progress = _paths(d, rnd)
    if not partial.exists():
        raise FileNotFoundError(f"no partial to commit: {partial} (flush the final round state first)")
    os.replace(partial, final)           # atomic
    _fsync_dir(rd)
    return str(final)


def _highest_round_with(d, suffix):
    rd = Path(d) / "rounds"
    if not rd.exists():
        return None
    rounds = [int(p.name.split(".")[0]) for p in rd.glob(f"*{suffix}")
              if p.name.split(".")[0].isdigit()]
    return max(rounds) if rounds else None


def resume_point(d):
    """Resume the HIGHEST round across partials+finals; prefer a partial only when the top round has one
    (a leftover lower-round partial must never roll a newer committed round backward)."""
    pr = _highest_round_with(d, ".json.partial")
    fr = _highest_round_with(d, ".json")
    cands = [r for r in (pr, fr) if r is not None]
    if not cands:
        return {"source": "none"}
    top = max(cands)
    _rd, _final, partial, _tmp, _progress = _paths(d, top)
    if partial.exists():
        st = json.loads(partial.read_text())          # raises on malformed — never silently wrong-state
        return {"round": top, "phase": st.get("phase"), "maxId": max_seq(d, top), "source": "partial"}
    return {"round": top, "phase": "complete", "maxId": max_seq(d, top), "source": "final"}


def load_state(d, rnd):
    _rd, final, partial, _tmp, _progress = _paths(d, rnd)
    for p in (partial, final):
        if p.exists():
            return json.loads(p.read_text())
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("flush", "commit", "max-seq", "next-id", "load"):
        s = sub.add_parser(name)
        s.add_argument("--dir", required=True)
        s.add_argument("--round", required=True)
        if name == "flush":
            s.add_argument("--phase", required=True)
    sub.add_parser("resume").add_argument("--dir", required=True)
    a = p.parse_args()

    if a.cmd == "flush":
        print(flush(a.dir, a.round, a.phase, json.load(sys.stdin)))
    elif a.cmd == "commit":
        print(commit(a.dir, a.round))
    elif a.cmd == "max-seq":
        print(max_seq(a.dir, a.round))
    elif a.cmd == "next-id":
        print(mint_next_id(a.dir, a.round))
    elif a.cmd == "resume":
        print(json.dumps(resume_point(a.dir)))
    elif a.cmd == "load":
        print(json.dumps(load_state(a.dir, a.round)))


if __name__ == "__main__":
    main()
