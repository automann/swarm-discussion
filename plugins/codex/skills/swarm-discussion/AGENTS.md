# swarm-discussion — repo invariants

Persistent instructions for this skill. Keep these true; they encode correctness, not style.

## Orchestration
- The discussion **orchestrator runs on the ROOT thread** (`agents.max_depth = 1` — it cannot be a
  subagent that spawns personas). Personas are spawned as parallel `swarm-expert` subagents.
- Personas are **runtime payloads**, not per-name agent files: one generic `agents/swarm-expert.toml`,
  with the specific persona + phase task + windowed slice injected in each spawn prompt.

## State & durability (see `protocol/durability.md`)
- The `rounds/{NNN}.json.partial` write-ahead log is the **system of record**; the root thread's memory is
  a cache. Flush per step (atomic `tmp`→`rename`); commit (`→ {NNN}.json`) at end of round.
- Mint message IDs durably from `max(existing id)+1` (grammar `r{N}-msg-{nnn}`); never restart at 001 on
  resume; resume prefers a `.partial` over the last completed round.
- Collect via `multi_agent_v1.wait_agent` (result map keyed by `agent_id`, payload a JSON string under
  `.completed`); demux by the spawn-time `agent_id→persona` map (each persona's `name`/`token` as a
  fallback) — never by arrival order. `report_agent_job_result` is not exposed on the app.

## Context discipline (see `protocol/windowing.md`)
- Position declarations are composed with **no peer content** (anti-anchoring).
- A persona's own declaration + shifts are **never windowed**; only peer bodies are. Every message ID is
  preserved verbatim. Any recorded position shift must cite an ID the persona was actually shown.

## Filesystem
- `discussionsRoot = ./.swarm/discussions` under the current workspace. Discussion artifacts are
  workspace-local; deleting a transient worktree deletes its local discussion artifacts too.
