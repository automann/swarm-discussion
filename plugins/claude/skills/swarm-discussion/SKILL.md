---
name: swarm-discussion
description: |
  Exploratory multi-expert discussion for unsolved problems. Experts debate over a shared blackboard with
  designed tension, blind position declarations, steel-manning, an argument graph, and quality gates.
---

# swarm-discussion

Use this skill as the orchestrator. Bundled files sit in this skill's own directory, exported to Bash as
**`${CLAUDE_SKILL_DIR}`**; Bash runs from the user's workspace, so reference them explicitly — read the
protocol docs below (they are skill-relative), and run the bundled Python helpers by absolute path,
`python3 "${CLAUDE_SKILL_DIR}/protocol/<name>.py" …`.

Load and follow these, then apply the runtime mapping:

1. [protocol/PROTOCOL.md](protocol/PROTOCOL.md) — orchestration (modes, roles, the round flow, synthesis).
2. [protocol/prompts.md](protocol/prompts.md) — prompt builders.
3. [protocol/SEAM.md](protocol/SEAM.md) — the six methods you implement here.
4. [protocol/durability.md](protocol/durability.md) — the write-ahead log (per-step flush, durable IDs, resume).
5. [protocol/windowing.md](protocol/windowing.md) — `sliceForPersona` + never-window-self-history + provenance.
6. [protocol/SCHEMA.md](protocol/SCHEMA.md) — the on-disk data contract. `discussionsRoot = ./.swarm/discussions`.

## Runtime mapping

| Seam method | Implementation |
|---|---|
| `spawnTeam(id)` | assert `python3 "${CLAUDE_SKILL_DIR}/protocol/wal.py" valid_discussion_id {id}`, then `Teammate({operation:"spawnTeam", team_name:"discussion-"+id})` + `mkdir -p .swarm/discussions/{id}/rounds` |
| `spawnPersona(name, prompt, {bg})` | `Task({team_name, name, subagent_type:"general-purpose", prompt, run_in_background:bg})` |
| `collectResult(name)` | `collectStatement(name)`, bound in `getDynamicExperts` order |
| `postToLog(entry)` | append to the in-memory round |
| `checkpoint(round, state, commit?)` | `python3 "${CLAUDE_SKILL_DIR}/protocol/wal.py" flush --dir .swarm/discussions/{id} --round N --phase P` (state on stdin) after every message-producing step; `commit:true` ⇒ flush the final state, then the same helper's `commit` (flush before commit). Seed the id counter from its `max-seq` at step entry. |
| `teardown()` | `Teammate(requestShutdown)` per worker, then `Teammate(cleanup)` |

Per-persona windowing and the provenance gate run as
`python3 "${CLAUDE_SKILL_DIR}/protocol/window.py" slice|provenance`; validate a committed round with
`python3 "${CLAUDE_SKILL_DIR}/protocol/validate_round.py" .swarm/discussions/{id}/rounds/NNN.json`.
Anything beyond this mapping belongs in the protocol docs, not here.
