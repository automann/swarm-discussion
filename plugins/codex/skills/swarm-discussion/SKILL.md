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
| `spawnPersona(name, promptPath, {bg})` | spawn the `swarm-expert` subagent with prompt text read from the runtime-produced `prompt.txt`; collect returned `{agentId, persona}` entries in `.swarm/discussions/{id}/tmp/spawn-order-rNNN-{phase}.json` |
| `collectResult(...)` (a step's batch) | after `transport-init`, write each raw `wait_agent` map to `.swarm/discussions/{id}/tmp/wait-batch.json` and run `transport-append-batch`; after all required agents complete, run `transport-collect` to write `transport/rNNN/{phase}/collect-result.json` through runtime `collect-merge`. **`wait_agent` may return partial batches** — poll until every spawn-order agent is complete before treating missing agents as failure. |
| `postToLog(entry)` | write `entry` to `.swarm/discussions/{id}/tmp/message.json`, then `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" append-message --dir .swarm/discussions/{id} --round N --phase P --message .swarm/discussions/{id}/tmp/message.json`; use `.result.message.id` as the durable message id |
| `checkpoint(round, state, commit?)` | write `state` to `.swarm/discussions/{id}/tmp/state.json`, then `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" checkpoint --dir .swarm/discussions/{id} --round N --phase P --state .swarm/discussions/{id}/tmp/state.json` after every step; `commit:true` ⇒ run `finalize-round --dir .swarm/discussions/{id} --round N --state .swarm/discussions/{id}/tmp/state.json`. Runtime WAL owns message-id minting, partial writes, progress, events, and final promotion. |
| `teardown()` | no-op (subagents are ephemeral); flip `manifest.status`; remove `.swarm/discussions/{id}/tmp/`. Close completed subagents between steps (agent-thread capacity). |

## Runtime-backed orchestration recipe (per round — wraps the seam calls in PROTOCOL.md)

For each spawn step (declarations / arguments / responses):
1. Build or refresh `.swarm/discussions/{id}/context/summary.md` with `context-build` from a compact
   `.swarm/discussions/{id}/tmp/brief.json` containing `topic`, `objective`, `mode`, `discussionId`,
   optional `parentContext`, `constraints`, `knownFacts`, and `successCriteria`.
2. For each persona, write a prompt-build request under
   `.swarm/discussions/{id}/prompts/rNNN/{phase}/{persona}/request.json`, then run
   `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" prompt-build --request ... --out-dir .swarm/discussions/{id}/prompts/rNNN/{phase}/{persona}`. Spawn `swarm-expert` with the produced `prompt.txt`.
3. Write the returned `{agentId, persona}` list to `.swarm/discussions/{id}/tmp/spawn-order-rNNN-{phase}.json`
   using the same persona order used for prompt-build. Then run:
   `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" transport-init --dir .swarm/discussions/{id} --host codex --discussion-id {id} --round N --phase P --spawn-order .swarm/discussions/{id}/tmp/spawn-order-rNNN-{phase}.json`
4. Poll `wait_agent`; for each raw batch, write `.swarm/discussions/{id}/tmp/wait-batch-rNNN-{phase}.json`
   and run:
   `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" transport-append-batch --dir .swarm/discussions/{id} --round N --phase P --wait-result .swarm/discussions/{id}/tmp/wait-batch-rNNN-{phase}.json`.
   After every spawn-order agent is complete, run:
   `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" transport-collect --dir .swarm/discussions/{id} --round N --phase P`.
5. For each collected persona result, call runtime `append-message` rather than minting ids in context. Use the
   returned message objects when constructing the in-memory round state.
6. `checkpoint` the round state after each step through the runtime wrapper. At round end, run
   `finalize-round` with the final round record; do not call legacy `wal.py flush` / `commit` for runtime-backed
   runs.

After responses: run the provenance gate (`python3 "$SWARM_DISCUSSION_SKILL_DIR/protocol/window.py" provenance`); any violation ⇒
fail the round + re-inject. Record `positionShifts[].trigger` as the real `shiftTriggerIds` array. Validate the
committed round with `python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" validate-round .swarm/discussions/{id}/rounds/NNN.json`.

For every runtime-backed spawn step, `transport-init` writes `host-step.json` with the thin parent context
surface: `briefPath`, `phase`, `agentIds`, and `nextHelperCommand`. Run the bundled smoke gate before
presenting final conclusions:

```
python3 "$SWARM_DISCUSSION_PLUGIN_ROOT/runtime/swarm_runtime_wrapper.py" adapter-smoke --dir .swarm/discussions/{id}
```

If runtime transport packet files are absent because the run explicitly used the legacy fallback path, continue
with legacy validation and state in the final summary that runtime transport smoke was not applicable for this
run.

**Execution notes:** feed helpers their JSON via temp files inside `.swarm/discussions/{id}/tmp/`; never use
user-scope `/tmp`, and never embed JSON literals directly in shell commands. Validate only committed
`rounds/NNN.json` records, never in-flight `.partial` files.
