---
name: swarm-discussion
description: |
  Exploratory multi-expert discussion for unsolved problems. A root-thread orchestrator coordinates
  ephemeral persona subagents over a shared write-ahead-log blackboard with designed tension,
  blind position declarations, steel-manning, an argument graph, and quality gates.
---

# swarm-discussion

Use this skill as the root-thread orchestrator. Bundled helpers live in this skill's installed directory.
Bash runs from the user's workspace, not from this directory, so begin every Bash block that calls a helper by
resolving the installed skill path:

```
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export SWARM_DISCUSSION_SKILL_DIR="${SWARM_DISCUSSION_SKILL_DIR:-$(find "$CODEX_HOME/plugins" "$CODEX_HOME/plugins/cache" "$CODEX_HOME/.tmp/marketplaces" -type f -path '*/skills/swarm-discussion/SKILL.md' 2>/dev/null | sort -V | tail -1 | sed 's#/SKILL.md$##')}"
```

`echo "$SWARM_DISCUSSION_SKILL_DIR"` must print a path ending `/skills/swarm-discussion` (if empty, stop; the
skill is not installed). Invoke every bundled helper by that variable, e.g.
`python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/<name>.py" ...`; never rely on the workspace cwd or hardcode an
absolute source-checkout path.

Before starting a discussion, run the bundled runtime preflight from the installed plugin root:

```
export SWARM_DISCUSSION_PLUGIN_ROOT="$(cd "$SWARM_DISCUSSION_SKILL_DIR/../.." && pwd -P)"
python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" doctor --smoke-fixture
```

Stop if this command fails. It proves the bundled runtime contract and its minimal fixture before any persona
spawns, without mutating the user's workspace.

Load and follow the protocol docs
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
| `spawnTeam(id)` | assert `python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/wal.py" valid_discussion_id {id}`, then `mkdir -p .swarm/discussions/{id}/{rounds,tmp}` |
| `spawnPersona(name, prompt, {bg})` | spawn the `swarm-expert` subagent with the composed `prompt`; **record the returned `agent_id` against `name`** (spawn-order list) |
| `collectResult(...)` (a step's batch) | write the accumulated `wait_agent` map to `.swarm/discussions/{id}/tmp/wait-result.json`, then `python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/collect.py" --spawn-order '<[{agentId,persona,token}]>' < .swarm/discussions/{id}/tmp/wait-result.json` → results in spawn order. **`wait_agent` may return a subset of completed targets even with `timed_out:false`** — poll the remaining agents, accumulate completed statuses into one map, THEN demux. `collect.py` `errors` for a not-yet-complete agent mean *poll again*; `errors`/`timedOut` after all targets are done ⇒ re-spawn. |
| `postToLog(entry)` | append to the in-memory round |
| `checkpoint(round, state, commit?)` | write `state` to `.swarm/discussions/{id}/tmp/state.json`, then `python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/wal.py" flush --dir .swarm/discussions/{id} --round N --phase P < .swarm/discussions/{id}/tmp/state.json` after every step; `commit:true` ⇒ flush the supplied final state, then the same helper's `commit` (flush before commit). Seed the id counter from its `max-seq`. |
| `teardown()` | no-op (subagents are ephemeral); flip `manifest.status`; remove `.swarm/discussions/{id}/tmp/`. Close completed subagents between steps (agent-thread capacity). |

## Orchestration recipe (per round — wraps the seam calls in PROTOCOL.md)

For each spawn step (declarations / arguments / responses):
1. `base = python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/wal.py" max-seq --dir .swarm/discussions/{id} --round N` → seed the in-context id counter.
2. **Response phase only:** per persona, write `{"messages":[...]}` to `.swarm/discussions/{id}/tmp/messages.json`, then `proj = python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/window.py" slice --persona P --phase response < .swarm/discussions/{id}/tmp/messages.json` → inject
   `proj.sliceText`, record `proj.visibility` into `personaContextLog[P]`. (Declarations are blind;
   argumentation passes `positionDeclarations`+`moderatorOpening`, not a slice.)
3. Spawn `swarm-expert` ×N; record each returned `agent_id` into the spawn-order list.
4. `wait_agent` (poll + accumulate until every spawn-order agent is present) → `protocol/collect.py` demux → results in
   spawn order. Mint ids `r{N}-msg-{base+i}`; build argument-graph edges from `references`.
5. `wal.py flush` the step via a temp-file payload under `.swarm/discussions/{id}/tmp/`.

After responses: run the provenance gate (`python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/window.py" provenance`); any violation ⇒
fail the round + re-inject. Record `positionShifts[].trigger` as the real `shiftTriggerIds` array. Round end:
build the round record, flush it (incl. `synthesis`), then `wal.py commit`. Validate a produced round with
`python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/validate_round.py" .swarm/discussions/{id}/rounds/NNN.json`.

If the discussion also wrote a runtime transport packet (`transport/**/host-step.json`, `spawn-order.json`,
`wait-batches.jsonl`, and `collect-result.json`), run the bundled smoke gate before presenting final
conclusions:

```
python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" adapter-smoke --dir .swarm/discussions/{id}
```

If those transport packet files are absent, continue with the legacy validation above and state in the final
summary that runtime transport smoke was not applicable for this run.

**Execution notes:** feed helpers their JSON via temp files inside `.swarm/discussions/{id}/tmp/`; never use
user-scope `/tmp`, and never embed JSON literals directly in shell commands. Validate only committed
`rounds/NNN.json` records, never in-flight `.partial` files.
