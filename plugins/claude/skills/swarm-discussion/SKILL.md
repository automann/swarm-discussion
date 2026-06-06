---
name: swarm-discussion
description: |
  Exploratory multi-expert discussion for unsolved problems. Experts debate over a shared blackboard with
  designed tension, blind position declarations, steel-manning, an argument graph, and quality gates.
---

# swarm-discussion

Use this skill as the orchestrator. Load and follow the protocol docs, then apply the Teammate runtime mapping
below:

1. `protocol/PROTOCOL.md` — orchestration (modes, roles, the round flow, synthesis).
2. `protocol/prompts.md` — prompt builders.
3. `protocol/SEAM.md` — the six methods you implement here.
4. `protocol/durability.md` — the write-ahead log (per-step flush, durable IDs, resume-from-partial).
5. `protocol/windowing.md` — `sliceForPersona` + never-window-self-history + shift provenance.
6. `protocol/SCHEMA.md` — the on-disk data contract. `discussionsRoot = ./.swarm/discussions`.

## Runtime mapping

| Seam method | Implementation |
|---|---|
| `spawnTeam(id)` | `Teammate({operation:"spawnTeam", team_name:"discussion-"+id})` + `mkdir -p .swarm/discussions/{id}` |
| `spawnPersona(name, prompt, {bg})` | `Task({team_name, name, subagent_type:"general-purpose", prompt, run_in_background:bg})` |
| `collectResult(name)` | `collectStatement(name)`, bound in `getDynamicExperts` order |
| `postToLog(entry)` | append to the in-memory round |
| `checkpoint(round, state, commit?)` | `python3 protocol/wal.py flush --dir .swarm/discussions/{id} --round N --phase P` (state on stdin) after every step; `commit:true` ⇒ flush the supplied final state, then `wal.py commit` (flush before commit). Seed the id counter from `wal.py max-seq` at step entry. |
| `teardown()` | `Teammate(requestShutdown)` per worker, then `Teammate(cleanup)` |

`sliceForPersona` (`window.py`) and the WAL `checkpoint` (`wal.py`) are shared helpers the protocol shells out
to. Anything beyond this mapping belongs in the protocol docs, not here.
