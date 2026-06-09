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

`live_runtime_flow.py` makes that live gate reproducible. `prepare` writes the
runtime-owned context and prompt artifacts plus an operator packet; after the
root thread records real spawn IDs and raw `wait_agent` batches, `finish` runs
runtime transport collection, WAL append/checkpoint/finalization, and the loop
validators. `self-test` covers missing spawn-order, partial fan-in, and a
complete simulated finish path.

`INSTALLED-RUNTIME-WRAPPER-SMOKE.md` records the clean-install gate for the
Codex plugin wrapper. It installs the plugin into a temporary `CODEX_HOME`, then
runs `doctor --smoke-fixture`, `runtime_flow_smoke.py --wrapper`, and
`live_runtime_flow.py --wrapper self-test` against the installed wrapper.

`CODEX-RUNTIME-FLOW-COMPLETION-AUDIT.md` is the requirement-by-requirement audit
for the Codex runtime-backed flow. It ties the natural skill entry, deterministic
smoke, live subagent smoke, and clean-install wrapper smoke back to the goal of
moving prompt-build, fan-in collection, and WAL ownership into runtime commands.
