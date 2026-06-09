# Live Runtime Flow Smoke

This gate proves the Codex runtime-backed flow with real `swarm-expert`
subagents. It is intentionally separate from CI because it requires the Codex
root thread to expose `multi_agent_v1.spawn_agent`, `wait_agent`, and
`close_agent`.

## Scope

The live boundary is:

1. Runtime wrapper writes `context/summary.md`.
2. Runtime wrapper writes two `prompt-build` artifacts and `prompt.txt` files.
3. The root thread spawns two real `swarm-expert` agents with those prompt
   files verbatim.
4. The root thread records only returned `agent_id` values and raw
   `wait_agent` batches.
5. Runtime wrapper owns `transport-init`, `transport-append-batch`,
   `transport-collect`, `append-message`, `checkpoint`, `finalize-round`,
   `trace`, `evidence`, `adapter-smoke`, and `validate-loop`.

The parent thread must not mint message IDs, hand-write standard transport
artifacts, or merge wait results outside runtime helpers.

## Latest Run

- Date: 2026-06-10
- Workspace: `/Users/syfq/dev/harness/swarm-discussion`
- Artifact root:
  `/tmp/swarm-live-runtime-flow.1781024899/.swarm/discussions/live-runtime-flow`
- Spawned agents:
  - architect: `019ead5b-c643-7c23-9800-70227c367388`
  - contrarian: `019ead5b-f01f-7633-a42d-3baea5cb3d74`

Evidence:

```json
{
  "partialMissingAgentIds": ["019ead5b-f01f-7633-a42d-3baea5cb3d74"],
  "messageIds": ["r1-msg-001", "r1-msg-002"],
  "waitBatchCount": 2,
  "collectResultCount": 1,
  "finalRoundCount": 1,
  "traceHealth": "on-track",
  "evidenceOutcome": "completed",
  "adapterSmokeOk": true,
  "validateLoopOk": true
}
```

The first `wait_agent` call returned only the architect result. The first
`transport-collect` correctly failed with the contrarian `agent_id` missing.
After the second raw wait batch was appended, `transport-collect` completed and
the same artifact tree passed `validate-round`, `trace`, `evidence`,
`adapter-smoke`, and `validate-loop`.

## Reproduction Checklist

1. Generate a temporary discussion directory outside the repo, for example
   `/tmp/swarm-live-runtime-flow.<id>/.swarm/discussions/live-runtime-flow`.
2. Use `python3 plugins/codex/runtime/swarm_runtime_wrapper.py context-build`
   to write `context/summary.md`.
3. Use `prompt-build` to write one prompt directory per persona.
4. Spawn `agent_type="swarm-expert"` once per generated `prompt.txt`.
5. Write a temporary spawn-order input containing only `{agentId, persona}`
   pairs from the spawn return values.
6. Run `transport-init`.
7. Append each raw `wait_agent` response with `transport-append-batch`.
8. Run `transport-collect` after each batch. A partial batch should fail with
   `missingAgentIds`; the complete set should pass.
9. Convert collected persona payloads into message payload files and call
   `append-message`.
10. Use `checkpoint` and `finalize-round` for WAL state.
11. Mark the manifest completed, write `artifacts/synthesis.md`, remove `tmp/`,
    then run `validate-round`, `trace`, `evidence`, `adapter-smoke`, and
    `validate-loop`.

The deterministic companion test is `conformance/runtime_flow_smoke.py`. It
simulates the spawn/wait boundary and should stay in CI; this live gate should
be rerun when changing Codex skill orchestration, custom-agent registration, or
transport/WAL handoff behavior.
