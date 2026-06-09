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
- Harness: `conformance/live_runtime_flow.py prepare` + `finish --require-partial`
- Artifact root:
  `/private/tmp/swarm-live-runtime-flow-1781025619/.swarm/discussions/live-runtime-flow`
- Spawned agents:
  - architect: `019ead66-9520-7840-89b2-2605d87f0a10`
  - contrarian: `019ead66-bd3a-7502-b741-6a4c75827ed5`

Evidence:

```json
{
  "partialMissingAgentIds": ["019ead66-bd3a-7502-b741-6a4c75827ed5"],
  "messageIds": ["r1-msg-001", "r1-msg-002"],
  "waitBatchCount": 2,
  "collectResultCount": 1,
  "promptBuildCount": 2,
  "finalRoundCount": 1,
  "traceHealth": "on-track",
  "evidenceOutcome": "completed",
  "adapterSmokeOk": true,
  "validateLoopOk": true
}
```

The harness `prepare` step generated the parent context summary and both persona
prompts. The first saved raw `wait_agent` batch contained only the architect
result, so the first `transport-collect` correctly failed with the contrarian
`agent_id` missing. After the second raw wait batch was appended,
`transport-collect` completed, runtime WAL minted `r1-msg-001` and
`r1-msg-002`, and the same artifact tree passed `validate-round`, `trace`,
`evidence`, `adapter-smoke`, and `validate-loop`.

## Reproduction Checklist

Use the two-phase harness whenever possible:

```sh
python3 conformance/live_runtime_flow.py prepare --root /tmp/swarm-live-runtime-flow.<id>
```

The `prepare` step writes `context/summary.md`, the two `prompt-build`
artifacts, `prompt.txt` files, and an `operator/live-runtime-flow-packet.json`.
From the Codex root thread:

1. Spawn `agent_type="swarm-expert"` once per packet prompt.
2. Save the returned agent IDs to `operator/spawn-order.json`.
3. Save each raw `wait_agent` response as `operator/wait-batch-N.json`.

Then finish the flow through runtime transport and WAL helpers:

```sh
python3 conformance/live_runtime_flow.py finish \
  --discussion-dir /tmp/swarm-live-runtime-flow.<id>/.swarm/discussions/live-runtime-flow \
  --spawn-order /tmp/swarm-live-runtime-flow.<id>/.swarm/discussions/live-runtime-flow/operator/spawn-order.json \
  --wait-result /tmp/swarm-live-runtime-flow.<id>/.swarm/discussions/live-runtime-flow/operator/wait-batch-1.json
```

Repeat `--wait-result` for each saved wait batch. Add `--require-partial` when
the run is intended to prove a partial `wait_agent` fan-in failure before the
complete batch arrives.

The deterministic companion tests are:

```sh
python3 conformance/live_runtime_flow.py self-test
python3 conformance/runtime_flow_smoke.py
```

`runtime_flow_smoke.py` simulates the spawn/wait boundary and should stay in CI.
Rerun the live gate when changing Codex skill orchestration, custom-agent
registration, or transport/WAL handoff behavior.
