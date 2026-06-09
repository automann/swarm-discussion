# Marketplace conformance

This repo ships vendored Claude and Codex plugin bundles. This harness verifies the packaged bundles still
preserve the shared protocol contract on their own, with no external dependencies.

Run:

```sh
python3 conformance/conformance.py
```

The script feeds identical canned persona outputs through the Claude-style collect path and the Codex
`wait_agent` + `collect.py` demux path, then asserts the produced round records are identical and pass the
vendored validator.

`runtime_flow_smoke.py` is the deterministic Codex runtime-backed flow smoke.
It starts from an empty discussion directory and composes `context-build`,
`prompt-build`, transport helpers, WAL helpers, `adapter-smoke`, and
`validate-loop`. It simulates the spawn/wait boundary so it can run in CI.

`LIVE-RUNTIME-FLOW-SMOKE.md` records the manual live gate for the same flow with
real `swarm-expert` subagents. Rerun that gate when changing Codex skill
orchestration, custom-agent registration, or transport/WAL handoff behavior.
