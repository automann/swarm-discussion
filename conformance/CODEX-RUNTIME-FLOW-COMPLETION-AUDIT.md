# Codex Runtime Flow Completion Audit

This audit checks whether the Codex plugin has replaced parent-thread
prompt-building, fan-in merging, and WAL ownership with runtime-backed commands
in the real discussion flow.

Date: 2026-06-10

## Scope

In scope:

- Codex plugin natural skill entry (`plugins/codex/skills/swarm-discussion/SKILL.md`).
- Codex plugin runtime wrapper (`plugins/codex/runtime/swarm_runtime_wrapper.py`).
- Bundled runtime primitives used by the Codex plugin.
- Deterministic flow smoke, live `swarm-expert` smoke, and clean-install
  installed-wrapper smoke.

Out of scope:

- Publishing a new npm installer release.
- Reworking the Claude plugin path.
- Replacing the remaining legacy protocol helpers that are still used for
  shared validation, provenance, discussion-id validation, or Claude parity.

## Requirement Audit

| Requirement | Current evidence | Status |
|---|---|---|
| Runtime builds persona prompts for the Codex path. | `SKILL.md` declares that the entry path is runtime-backed by default and forbids deriving persona prompt text without `prompt-build`. The runtime-backed recipe calls `prompt-build` for each persona and spawns `swarm-expert` with the produced `prompt.txt`. `conformance.py` guards those statements. `runtime_flow_smoke.py` proves two prompt artifacts are generated from an empty discussion tree. `LIVE-RUNTIME-FLOW-SMOKE.md` records a real `swarm-expert` run using runtime-produced prompts. | Complete |
| Fan-in is keyed by returned Codex `agent_id`, not persona names or parent-side merge logic. | `SKILL.md` states fan-in is keyed by returned `agent_id`, uses `transport-init`, preserves raw `wait_agent` batches with `transport-append-batch`, and completes with `transport-collect` / runtime `collect-merge`. It forbids merging `wait_agent` statuses outside those runtime commands. `runtime_flow_smoke.py` proves partial fan-in fails before completion. `LIVE-RUNTIME-FLOW-SMOKE.md` records the same failure with real `swarm-expert` agents. `conformance.py` guards the natural entry against `protocol/collect.py` fallback. | Complete |
| Runtime owns WAL message IDs, checkpointing, events, and final round promotion. | `SKILL.md` routes log writes through `append-message`, checkpoints through `checkpoint`, and final promotion through `finalize-round`; it forbids minting message IDs, editing committed rounds, patching partial WAL files, or calling legacy `wal.py flush` / `commit` for runtime-backed runs. `conformance.py` proves wrapper `append-message` mints `r1-msg-001`, accepts references, and `finalize-round` commits a round. Runtime flow and live smoke both produce `r1-msg-001` and `r1-msg-002` through runtime commands. | Complete |
| Runtime artifacts are required and missing artifacts fail closed. | `SKILL.md` requires runtime-backed runs to produce `transport/**/host-step.json` and `transport/**/collect-result.json`, and says missing runtime artifacts are incomplete rather than a reason to downgrade. `conformance.py` guards this wording. `live_runtime_flow.py self-test` covers missing spawn-order and partial fan-in failures before WAL. | Complete |
| Installed Codex plugin uses the same runtime-backed behavior, not only the source checkout. | `INSTALLED-RUNTIME-WRAPPER-SMOKE.md` records a clean `CODEX_HOME` install of `swarm-discussion@swarm-discussion` version `0.1.11`. The installed wrapper passes `doctor --smoke-fixture`, `runtime_flow_smoke.py --wrapper`, and `live_runtime_flow.py --wrapper self-test`. | Complete |
| The live host boundary has been validated with real Codex subagents. | `LIVE-RUNTIME-FLOW-SMOKE.md` records a `prepare` + `finish --require-partial` run with two real `swarm-expert` subagents. Runtime prepared context and prompts, the root thread saved only returned agent IDs and raw wait batches, the first collect failed on the missing contrarian agent ID, and the final artifact tree passed `validate-round`, `trace`, `evidence`, `adapter-smoke`, and `validate-loop`. | Complete |

## Verification Commands

The current checkout passes:

```sh
python3 conformance/conformance.py
git diff --check
```

The clean-install gate recorded in `INSTALLED-RUNTIME-WRAPPER-SMOKE.md` uses:

```sh
TMP_CODEX_HOME="$(mktemp -d /tmp/swarm-installed-wrapper-audit.XXXXXX)"
CODEX_HOME="$TMP_CODEX_HOME" codex plugin marketplace add automann/swarm-discussion --ref main
CODEX_HOME="$TMP_CODEX_HOME" codex plugin add swarm-discussion@swarm-discussion

INSTALLED_WRAPPER="$(find "$TMP_CODEX_HOME/plugins/cache/swarm-discussion/swarm-discussion" \
  -path '*/runtime/swarm_runtime_wrapper.py' | sort -V | tail -1)"
python3 "$INSTALLED_WRAPPER" doctor --smoke-fixture
python3 conformance/runtime_flow_smoke.py --wrapper "$INSTALLED_WRAPPER"
python3 conformance/live_runtime_flow.py --wrapper "$INSTALLED_WRAPPER" self-test
```

## Conclusion

For the Codex plugin, `prompt-build`, runtime fan-in collection, and runtime WAL
commands have replaced the parent-thread implementation in the natural
discussion path. The root thread remains a thin host operator for Codex
spawn/wait/close and temp input handoff; standard prompt, transport, collect,
message-id, checkpoint, finalization, trace, evidence, and loop-validation
artifacts are owned by runtime commands.

