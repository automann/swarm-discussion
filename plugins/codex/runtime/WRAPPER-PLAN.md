# Codex Wrapper Migration Plan

The goal was to move Codex orchestration mechanics out of the parent
conversation while keeping the published plugin usable throughout the migration.

Current status: **P0-P4 are complete as of Codex plugin 0.1.11**. The natural
Codex skill entry is runtime-backed by default. The root thread still owns only
Codex host operations that cannot be delegated to the runtime: spawn
`swarm-expert`, wait for returned results, close completed agents, and pass raw
host evidence into runtime commands.

## Current Operating Model

- The skill runs `doctor --smoke-fixture` before persona work.
- The runtime owns parent-context summaries and persona prompt artifacts through
  `context-build` and `prompt-build`.
- The runtime owns host transport artifacts through `transport-init`,
  `transport-append-batch`, and `transport-collect`.
- Fan-in is keyed by returned Codex `agent_id`; persona names are metadata.
- The runtime owns message-id minting, checkpoints, event logs, and final round
  promotion through `append-message`, `checkpoint`, and `finalize-round`.
- The skill fails closed when runtime transport artifacts are missing; it does
  not silently downgrade to legacy validation.

Completion evidence is recorded in:

- `conformance/CODEX-RUNTIME-FLOW-COMPLETION-AUDIT.md`
- `conformance/LIVE-RUNTIME-FLOW-SMOKE.md`
- `conformance/INSTALLED-RUNTIME-WRAPPER-SMOKE.md`
- `conformance/runtime_flow_smoke.py`
- `conformance/live_runtime_flow.py`

## Completed Migration

### P0: Wrapper Skeleton

Status: complete.

Delivered:

- Plugin-side wrapper resolves the runtime CLI.
- Wrapper verifies `runtime-contract` and `swarm-runtime-v2-alpha`.
- Wrapper delegates gates and primitives without copying runtime semantics.

Evidence:

- `conformance/conformance.py` fake-runtime delegation checks.
- `python3 plugins/codex/runtime/swarm_runtime_wrapper.py doctor`.

### P1: Package Boundary

Status: complete.

Delivered:

- Runtime package is vendored into the Codex plugin.
- External `swarm-rt` remains only a development override.
- Bundled minimal fixture can be replayed from the installed plugin root.

Evidence:

- `doctor --smoke-fixture`.
- `conformance/INSTALLED-RUNTIME-WRAPPER-SMOKE.md`.

### P2: Adapter-Facing Smoke In The Plugin

Status: complete.

Delivered:

- Skill runs `adapter-smoke` against completed discussion artifacts.
- Runtime `host-step.json` records the thin parent-context surface.
- Runtime trace/evidence output is the audit summary.

Evidence:

- `plugins/codex/skills/swarm-discussion/SKILL.md`.
- `conformance/runtime_flow_smoke.py`.
- `conformance/LIVE-RUNTIME-FLOW-SMOKE.md`.

### P3: Runtime-Owned Prompt And WAL

Status: complete.

Delivered:

- Manual prompt construction is replaced by `context-build` and `prompt-build`.
- Manual fan-in merge is replaced by transport helpers and runtime
  `collect-merge`.
- Manual id minting and checkpointing are replaced by runtime WAL commands.

Evidence:

- `conformance/CODEX-RUNTIME-FLOW-COMPLETION-AUDIT.md`.
- `conformance/conformance.py` entry-contract guards.

### P4: Default Runtime Path

Status: complete.

Delivered:

- Runtime-backed path is the default Codex skill entry contract.
- Legacy runtime fallback is not an automatic downgrade path.
- Clean-install and live smoke evidence are recorded.

Evidence:

- Codex plugin manifest version `0.1.11`.
- `conformance/INSTALLED-RUNTIME-WRAPPER-SMOKE.md`.
- `conformance/LIVE-RUNTIME-FLOW-SMOKE.md`.

## Next Stages

### P5: Installer Runtime Awareness

Status: complete in `swarm-discussion-installer` `0.1.3` source, not yet
published.

The wrapper installer now treats Codex's versioned plugin cache as the installed
plugin root:

- `doctor` reports the active plugin-list version, listed marketplace path,
  installed cache root, installed wrapper path, and `doctor --smoke-fixture`
  outcome.
- `install` / `repair` copy `agents/swarm-expert.toml` from
  `CODEX_HOME/plugins/cache/swarm-discussion/swarm-discussion/<version>/`
  before running the same doctor gate; `--verify-spawn` still adds the opt-in
  real Codex spawn smoke after registration.
- `repair` detects stale custom-agent registration through the existing
  overwrite policy, and `doctor` warns on stale cache versions beside the active
  cache while failing when the active cache root is missing.

Evidence:

- `npm test` in `/Users/syfq/dev/harness/swarm-discussion-installer`: 31/31
  passed.
- Isolated `CODEX_HOME` smoke ran `install --project`, `doctor`, and
  `uninstall --project --all`; install copied from the `0.1.11` cache root and
  doctor validated the cache wrapper fixture smoke.

### P6: Runtime/Plugin Drift Guard

The runtime source repo and vendored plugin copy must stay in lockstep.

Candidate acceptance:

- A sync or audit command compares runtime command surfaces, contract JSON, and
  vendored source hashes.
- CI fails if the plugin advertises a runtime command absent from the vendored
  runtime.
- Completion audit docs point to the exact installed plugin version used for
  smoke evidence.

### P7: Richer Real-Run Coverage

The current live smoke proves a lightweight declaration step with two real
subagents. Broader live coverage can now move up the protocol stack.

Candidate acceptance:

- A standard-mode smoke covers declaration, argumentation, response, and
  provenance gates.
- Failure evidence includes an incomplete transport run and a WAL resume run.
- The artifact tree alone is sufficient to diagnose the next action without
  replaying the parent transcript.
