---
name: swarm-discussion
description: |
  Exploratory multi-expert discussion for unsolved problems. A root-thread orchestrator coordinates
  ephemeral persona subagents over a shared write-ahead-log blackboard with designed tension,
  blind position declarations, steel-manning, an argument graph, and quality gates.
---

# swarm-discussion

Use this skill as the root-thread orchestrator. Load and follow the protocol docs
(`protocol/PROTOCOL.md`, `SEAM.md`, `durability.md`, `windowing.md`, `SCHEMA.md`, `prompts.md`),
then apply the runtime mapping below.

## Runtime constraints

- **Run on the ROOT thread** — `agents.max_depth = 1` forbids the orchestrator from being a subagent that
  spawns personas. The user invokes the skill at top level.
- `discussionsRoot = ./.swarm/discussions` under the current workspace. Discussions are workspace-local; if a
  worktree is deleted, its local discussion artifacts are deleted with it.
- Personas are not per-name agent files: spawn the single generic `agents/swarm-expert.toml` and inject the
  persona + phase task + (response phase) windowed slice in the prompt. The spawn prompt must ask the persona
  to echo its `name`/`token` (for the collect fallback).

## Runtime mapping

| Seam method | Implementation |
|---|---|
| `spawnTeam(id)` | assert `wal.py valid_discussion_id {id}`, then `mkdir -p .swarm/discussions/{id}/rounds` |
| `spawnPersona(name, prompt, {bg})` | spawn the `swarm-expert` subagent with the composed `prompt`; **record the returned `agent_id` against `name`** (spawn-order list) |
| `collectResult(...)` (a step's batch) | `multi_agent_v1.wait_agent`, then `python3 protocol/collect.py --spawn-order '<[{agentId,persona,token}]>' < wait_result.json` → results in spawn order. **`wait_agent` may return a subset of completed targets even with `timed_out:false`** — poll the remaining agents, accumulate completed statuses into one map, THEN demux. `collect.py` `errors` for a not-yet-complete agent mean *poll again*; `errors`/`timedOut` after all targets are done ⇒ re-spawn. |
| `postToLog(entry)` | append to the in-memory round |
| `checkpoint(round, state, commit?)` | `python3 protocol/wal.py flush --dir .swarm/discussions/{id} --round N --phase P` (state on stdin) after every step; `commit:true` ⇒ flush the supplied final state, then `wal.py commit` (flush before commit). Seed the id counter from `wal.py max-seq`. |
| `teardown()` | no-op (subagents are ephemeral); flip `manifest.status`. Close completed subagents between steps (agent-thread capacity). |

## Orchestration recipe (per round — wraps the seam calls in PROTOCOL.md)

For each spawn step (declarations / arguments / responses):
1. `base = wal.py max-seq` → seed the in-context id counter.
2. **Response phase only:** per persona, `proj = window.py slice --persona P --phase response` → inject
   `proj.sliceText`, record `proj.visibility` into `personaContextLog[P]`. (Declarations are blind;
   argumentation passes `positionDeclarations`+`moderatorOpening`, not a slice.)
3. Spawn `swarm-expert` ×N; record each returned `agent_id` into the spawn-order list.
4. `wait_agent` (poll + accumulate until every spawn-order agent is present) → `protocol/collect.py` demux → results in
   spawn order. Mint ids `r{N}-msg-{base+i}`; build argument-graph edges from `references`.
5. `wal.py flush` the step.

After responses: run the provenance gate (`python3 protocol/window.py provenance`); any violation ⇒
fail the round + re-inject. Record `positionShifts[].trigger` as the real `shiftTriggerIds` array. Round end:
build the round record, flush it (incl. `synthesis`), then `wal.py commit`. Validate a produced round with
`python3 protocol/validate_round.py rounds/NNN.json`.
