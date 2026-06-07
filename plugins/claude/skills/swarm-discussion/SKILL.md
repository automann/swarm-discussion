---
name: swarm-discussion
description: |
  Exploratory multi-expert discussion for unsolved problems. Experts debate over a shared blackboard with
  designed tension, blind position declarations, steel-manning, an argument graph, and quality gates.
---

# swarm-discussion

Use this skill as the orchestrator. Bundled helpers live in this skill's installed directory, but
`${CLAUDE_SKILL_DIR}` may be **empty** in Bash — so begin every Bash block that calls a helper by resolving it,
falling back to the installed cache:

```
export CLAUDE_SKILL_DIR="${CLAUDE_SKILL_DIR:-$(find ~/.claude/plugins/cache -type d -path '*/swarm-discussion/*/skills/swarm-discussion' 2>/dev/null | sort -V | tail -1)}"
```

`echo "${CLAUDE_SKILL_DIR}"` must then print a path ending `/skills/swarm-discussion` (if still empty, stop —
the skill is not installed). Bash runs from the user's workspace, not this dir, so invoke every bundled helper
by that variable — `python3 "${CLAUDE_SKILL_DIR}/protocol/<name>.py" …` — and **never hardcode an absolute
path**. Read the protocol docs below as skill-relative links (resolved from this dir):

Load and follow these, then apply the runtime mapping:

1. [protocol/PROTOCOL.md](protocol/PROTOCOL.md) — orchestration (modes, roles, the round flow, synthesis).
2. [protocol/prompts.md](protocol/prompts.md) — prompt builders.
3. [protocol/SEAM.md](protocol/SEAM.md) — the six methods you implement here.
4. [protocol/durability.md](protocol/durability.md) — the write-ahead log (per-step flush, durable IDs, resume).
5. [protocol/windowing.md](protocol/windowing.md) — `sliceForPersona` + never-window-self-history + provenance.
6. [protocol/SCHEMA.md](protocol/SCHEMA.md) — the on-disk data contract. `discussionsRoot = ./.swarm/discussions`.

## Runtime mapping

Personas are spawned as the bundled **`swarm-expert`** agent (`agents/swarm-expert.md`), which carries the
"embody the persona, cite only provided IDs, return ONLY the requested JSON" contract — so the specific
persona, phase task, and windowed slice go in the spawn `prompt`, and the agent returns a single JSON object.

| Seam method | Implementation |
|---|---|
| `spawnTeam(id)` | assert `python3 "${CLAUDE_SKILL_DIR}/protocol/wal.py" valid_discussion_id {id}`, then `mkdir -p .swarm/discussions/{id}/{rounds,tmp}` |
| `spawnPersona(name, prompt, {bg})` | `Agent({subagent_type:"swarm-discussion:swarm-expert", description:name, prompt, run_in_background:bg})` — spawn a step's personas in parallel |
| `collectResult(name)` | take the spawned agent's returned final message and parse its JSON, bound in `getDynamicExperts` spawn order. If the reply is not pure JSON, extract the first `{…}` object before falling back to a re-spawn. |
| `postToLog(entry)` | append to the in-memory round |
| `checkpoint(round, state, commit?)` | `python3 "${CLAUDE_SKILL_DIR}/protocol/wal.py" flush --dir .swarm/discussions/{id} --round N --phase P` (state on stdin) after every message-producing step; `commit:true` ⇒ flush the final state, then the same helper's `commit` (flush before commit). Seed the id counter from its `max-seq` at step entry. |
| `teardown()` | no-op (persona agents are ephemeral); set `manifest.status`; remove the `{id}/tmp/` scratch dir. |

Per-persona windowing and the provenance gate run as
`python3 "${CLAUDE_SKILL_DIR}/protocol/window.py" slice|provenance`. Validate a **committed** round with
`python3 "${CLAUDE_SKILL_DIR}/protocol/validate_round.py" .swarm/discussions/{id}/rounds/NNN.json` — never the
in-flight `.partial` (different shape; it reports failures).

**Execution notes:** feed helpers their JSON via a temp file **inside the discussion dir** and pipe it (e.g.
`< .swarm/discussions/{id}/tmp/state.json`) — never user-scope `/tmp`, and never embed a JSON literal directly
in the Bash command (it breaks shell quoting). Read any artifact / `manifest.json` before you Write or Edit it.

Anything beyond this mapping belongs in the protocol docs, not here.
