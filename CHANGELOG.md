# Changelog

All notable changes to swarm-discussion. Versioning is SemVer; the on-disk data contract is versioned
separately as `schemaVersion` (see the vendored `protocol/SCHEMA.md` under each plugin bundle).

## [0.3.0] - 2026-06-21 - Claude adapter v0.3.0 (dynamic custom-agent topology)

- Pin the Claude adapter at `v0.3.0`: the parent projects per-topic run-scoped
  custom expert agents and dispatches a `swarm-coordinator` background session
  that runs the discussion and spawns them, with runtime-owned projection
  provenance (vendored runtime `04f4974`). Certified with
  `certify_adapter.py --require-projection` against a real coordinator-driven
  projected discussion (5/5) plus a zero-residue cleanup check.
- The Codex adapter (`.agents/plugins/marketplace.json`) stays on its current pin
  until it re-vendors at `04f4974` and certifies `--require-projection`.

## [0.2.2] - 2026-06-21 - Add Codex root plugin marketplace entry

- Add `.agents/plugins/marketplace.json` for Codex, pointing at
  `automann/swarm-discussion-codex` release tag `v0.2.2`.
- Update README install instructions for Codex while preserving this repository
  as a thin aggregator with no runtime or plugin payload code.
- Extend CI marketplace validation to cover both Claude and Codex host
  manifests and to allow only the Codex marketplace manifest under `.agents/`.

## [0.2.1] - 2026-06-19 - Ship runtime fixes (Codex-found)

- Pin the Claude adapter at `v0.2.1`, which vendors runtime `93e99d1`:
  - Stable artifact byte total — `build_trace`/`build_evidence` are now idempotent (trace/evidence/metrics
    agree), and `validate-loop` catches stale trace/evidence anchors.
  - Command surface converged (`persona-plan` removed; `planned_commands()` == CLI parser == contract,
    pinned by a drift test).
- Internal correctness + audit-integrity fixes only; no end-user behavior change.

## [0.2.0] - 2026-06-11 - Thin aggregator + adapter split

- swarm-discussion is now a thin aggregator marketplace. Protocol semantics, runtime mechanics, schemas, and
  the certification gates live in `swarm-discussion-runtime`; each host adapter is its own repo that vendors
  the runtime at a pinned SHA.
- `.claude-plugin/marketplace.json` points at the certified Claude adapter release
  (`automann/swarm-discussion-claude` @ `v0.2.0`), which uses the orchestrator-as-sub-agent topology so
  discussion mechanics stay out of the parent context window.
- Removed the bundled dual-host plugins, vendored runtime, and conformance harness from this repo. The
  previous single-repo line is preserved at the `v0.1.16` tag and `v0.1.x` branch.
- The Codex adapter (`swarm-discussion-codex`) will be listed here once it certifies.

## [0.1.16] - 2026-06-10 - Codex runtime-backed entry contract (Codex 0.1.11)

- Codex `SKILL.md` now declares the runtime-backed path as the default entry contract: the root thread may
  prepare compact temp inputs and call Codex spawn/wait/close, but must not build prompts, merge fan-in, mint
  message IDs, patch WAL files, or substitute fixture-only validation for the actual discussion artifact tree.
- Conformance now guards that contract so the natural Codex skill entry cannot drift back to parent-side
  prompt/fan-in/WAL orchestration.
- Refreshed the installed-wrapper smoke audit against a clean `0.1.11` Codex plugin install.
- Added a completion audit tying the natural skill entry, deterministic smoke, live subagent smoke, and
  clean-install wrapper smoke back to runtime ownership of prompt-build, fan-in collection, and WAL.
- Synced the public README and Codex wrapper migration plan with the completed `0.1.11` runtime-backed default
  path, and added conformance guards against stale bundled-helper wording.
- Recorded the installer runtime-awareness closeout: installer `doctor` / `install` / `repair` now validate
  the versioned Codex plugin cache wrapper path before treating the install as healthy.
- Bumped the Codex bundle to `0.1.11`.

## [0.1.15] - 2026-06-10 - Codex runtime-owned transport artifacts (Codex 0.1.10)

- Vendored runtime now includes `transport-init`, `transport-append-batch`, and `transport-collect`, so the
  runtime writes `host-step.json`, `spawn-order.json`, `wait-batches.jsonl`, and `collect-result.json`.
- Codex `SKILL.md` now routes spawn/wait artifact handling through those transport helpers instead of asking
  the parent thread to hand-write standard transport files.
- Wrapper conformance now proves the new transport helper roundtrip and requires the commands in the runtime
  contract.
- Added an end-to-end runtime-backed flow smoke that composes `context-build`, `prompt-build`, transport
  helpers, WAL commands, `adapter-smoke`, and `validate-loop` from an empty discussion directory.
- Added a manual live-smoke audit proving the same flow with real `swarm-expert` subagents and partial
  `wait_agent` fan-in.
- Added a two-phase live-smoke harness (`conformance/live_runtime_flow.py`) that prepares runtime prompts,
  lets the operator save real spawn/wait evidence, then finishes transport collection, WAL finalization, and
  loop validation through runtime commands.
- Refreshed the live-smoke audit with the harness path and real `swarm-expert` agents, including a required
  partial fan-in failure before the final collect succeeds.
- Added an installed-wrapper smoke audit showing a clean marketplace install can run the bundled runtime
  preflight, deterministic runtime flow smoke, and live harness self-test through the installed wrapper.
- Codex `SKILL.md` now treats missing runtime transport artifacts as incomplete instead of silently
  downgrading to legacy validation.
- Bumped the Codex bundle to `0.1.10`.

## [0.1.14] - 2026-06-10 - Codex runtime primitive handoff (Codex 0.1.9)

- Codex runtime wrapper now delegates stable runtime primitives (`context-build`, `prompt-build`,
  `collect-merge`, `append-message`, `checkpoint`, `finalize-round`, validators, trace/evidence) in addition
  to smoke gates.
- Codex `SKILL.md` now instructs runtime-backed runs to use runtime prompt artifacts, runtime fan-in merge, and
  runtime WAL message-id/checkpoint/finalization commands rather than context-minted ids and legacy WAL flushes.
- Bumped the Codex bundle to `0.1.9`.

## [0.1.13] - 2026-06-10 - Codex runtime preflight in skill (Codex 0.1.8)

- Codex `SKILL.md` now runs the bundled runtime wrapper `doctor --smoke-fixture` before discussion work starts,
  so the vendored runtime is part of the real skill execution path.
- Codex skill path discovery now includes marketplace-installed plugin roots under
  `$CODEX_HOME/.tmp/marketplaces`, matching clean-install plugin list output.
- Added a final runtime smoke gate instruction for runs that produce runtime transport packet artifacts.
- Bumped the Codex bundle to `0.1.8`.

## [0.1.12] - 2026-06-10 - Codex bundled fixture smoke (Codex 0.1.7)

- Added a bundled minimal runtime fixture under `plugins/codex/runtime/fixtures/minimal-v2`.
- Codex runtime wrapper `doctor --smoke-fixture` now verifies the bundled runtime contract and runs
  `adapter-smoke` against the fixture without spawning agents or mutating state.
- Extended conformance coverage for the bundled fixture smoke.
- Bumped the Codex bundle to `0.1.7`.

## [0.1.11] - 2026-06-10 - Codex bundled runtime bridge (Codex 0.1.6)

- Added a Codex plugin-side runtime wrapper under `plugins/codex/runtime/`. It resolves a
  compatible v2 runtime CLI, verifies `runtime-contract`, and delegates `adapter-smoke` / `validate-loop`
  without copying prompt, fan-in, WAL, trace, or evidence logic into the plugin.
- Vendored the v2 runtime package into the Codex plugin root so production installs can use a version-coupled
  bundled runtime instead of depending on a global `swarm-rt`.
- Added a Codex wrapper migration plan documenting the staged path from legacy bundled-helper orchestration to
  a runtime-backed plugin flow.
- Extended conformance coverage so the wrapper is exercised against a fake compatible runtime.
- Bumped the Codex bundle to `0.1.6`.

## [0.1.10] - 2026-06-08 - Codex bundle adapter hardening (Codex 0.1.5)

- Codex SKILL.md now resolves bundled helpers from the installed skill directory before helper calls, instead
  of relying on the workspace cwd.
- Codex runtime mapping now creates `{rounds,tmp}`, stages helper JSON payloads under `{id}/tmp/`, removes
  that scratch dir at teardown, and documents committed-round-only validation (`rounds/NNN.json`, never
  `.partial`).
- CI runtime-wording guard now strips the required Codex path variable names before checking skill files.

## [0.1.9] - 2026-06-08 - lighter lightweight tier (R2)

- Lightweight mode now runs the quality gate, synthesis, and resume-context **inline** (orchestrator, no extra
  subagent spawns) and writes a single concise `synthesis.md` instead of the full Historian + 5-artifact pass —
  cutting ~3 spawns and the heaviest step per lightweight run, while keeping the multi-agent debate (independent
  experts + Contrarian, blind declarations, position shifts) intact. Standard/Deep unchanged.
- README footprint documents realistic cost. Shared `protocol/` re-synced to both bundles (Claude 0.1.9, Codex 0.1.4).

## [0.1.8] - 2026-06-08 - scratch under the discussion dir (M2)

- Transient helper payloads (the JSON piped to `wal.py`/`window.py`) now live under
  `{discussionsRoot}/{id}/tmp/` instead of user-scope `/tmp` — created at `spawnTeam`, removed at `teardown`.
  Keeps every write inside the discussion dir (no `/tmp` collisions between concurrent discussions). SKILL.md
  execution note + SCHEMA.md layout updated. Claude → 0.1.8, Codex → 0.1.3 (shared SCHEMA.md re-synced).

## [0.1.7] - 2026-06-08 - shared core: deterministic termination + manifest schema (M3/M4)

- **M3:** PROTOCOL.md Phase 4 now ALWAYS writes `context/summary.md` (resume context) — on completion and on a
  mid-discussion pause, every mode — instead of inconsistently skipping it.
- **M4:** pinned `manifest.personas` to the FULL persona records (objects, not ids) in PROTOCOL.md + SCHEMA.md.
- Shared `protocol/` change — re-synced into both bundles (Claude → 0.1.7, Codex → 0.1.2).

## [0.1.6] - 2026-06-08 - Claude Code: deterministic skill-dir resolution (C2b)

- SKILL.md no longer assumes `${CLAUDE_SKILL_DIR}` is populated in Bash (the clean-install test showed it
  empty). Each helper block now resolves it with a cache fallback —
  `export CLAUDE_SKILL_DIR="${CLAUDE_SKILL_DIR:-$(find ~/.claude/plugins/cache … | sort -V | tail -1)}"` — so
  resolution is deterministic instead of relying on the model to locate the install path.
- CI: the runtime-wording invariant strips the `claude_skill_dir` / `claude_plugin_root` identifiers and the
  `.claude/plugins` cache-path prefix (paths/vars, not cross-host prose).

## [0.1.5] - 2026-06-08 - Claude Code: orchestration hardening (R3)

- SKILL.md execution notes: feed bundled helpers their JSON via a temp file (not an inline Bash literal —
  avoids shell-quoting failures), Read before Write/Edit, and validate only the committed `rounds/NNN.json`,
  never the in-flight `.partial`. Addresses the three self-recovered orchestration soft-errors observed in the
  0.1.3 run (`e99c5228`).

## [0.1.4] - 2026-06-08 - Claude Code: consume the injected ${CLAUDE_SKILL_DIR}

- SKILL.md now directs the orchestrator to confirm (`echo`) and use the injected `${CLAUDE_SKILL_DIR}` for all
  bundled-helper calls, and to never hardcode an absolute path or assume a source checkout — so helpers resolve
  from the installed location on any machine. Addresses backlog C2 (both prior live runs hardcoded the
  source-repo path because the repo happened to be the working directory).
- CI: the runtime-wording invariant also allows the bare `$CLAUDE_SKILL_DIR` / `$CLAUDE_PLUGIN_ROOT` forms.

## [0.1.3] - 2026-06-08 - Claude Code: dedicated swarm-expert agent + real tool mapping

- Added a bundled `swarm-expert` agent (`plugins/claude/agents/swarm-expert.md`); personas now spawn via
  `Agent(subagent_type:"swarm-discussion:swarm-expert")` instead of `general-purpose`. The agent carries the
  "embody the persona, cite only provided IDs, return ONLY the requested JSON" contract, removing the
  output-conformance re-spawns observed in testing. (The `Read` tool is retained for future needs.)
- Rewrote the Claude runtime mapping to the actual tool surface — `Agent` for spawn, the returned message for
  collect, `mkdir` for team setup — retiring the stale `Teammate` / `Task` / `collectStatement` references.
- Added a tolerant-parse step (extract the first JSON object) so a non-pure-JSON reply doesn't force a re-spawn.

## [0.1.2] - 2026-06-07 - Claude Code helper path resolution

- Claude Code bundle: read protocol docs and invoke vendored helpers via the `${CLAUDE_SKILL_DIR}` plugin
  variable instead of workspace-relative paths, so `/swarm-discussion` resolves `protocol/wal.py`,
  `window.py`, `validate_round.py`, and the protocol docs regardless of the user's working directory.
- Added the discussion-id validation step to the Claude Code `spawnTeam` mapping, for parity with the schema
  and the other bundle.
- CI: allow the `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` runtime path variables in the runtime-wording
  invariant (they are required path tokens, not cross-host prose).

## [0.1.1] - 2026-06-07 - Codex helper contract fix

- Added the `wal.py valid_discussion_id` CLI command required by the Codex and schema docs, plus a
  `valid-discussion-id` alias.
- Added a Codex `protocol/collect.py` compatibility entrypoint so runtime docs can resolve fan-in demux
  relative to the protocol helper directory.
- Added conformance coverage for discussion-id validation and Codex protocol collect wrapper behavior.

## [0.1.0] — 2026-06-05 — cross-platform port (Claude Code + Codex)

First dual-host release. The skill is re-architected as **one shared protocol body + thin host adapters**
(no fork), shipped as two native plugins over a vendored shared core.

### Added
- **Shared core** (vendored `protocol/` under each bundle): host-neutral orchestration (`PROTOCOL.md`, `prompts.md`), the 6-method
  transport seam (`SEAM.md`), the on-disk data contract (`SCHEMA.md`, **schemaVersion 2**), and tested
  helpers — `wal.py` (write-ahead-log durability), `window.py` (context windowing + shift provenance),
  `validate_round.py` (round-record validator).
- **Codex bundle** (`plugins/codex/`): native-subagent orchestration, `collect.py` (the
  `multi_agent_v1.wait_agent` → spawn-order demux), generic `swarm-expert` agent, and install-only behavior.
  Both bundles default to workspace-local discussion storage under `.swarm/discussions`.
- **Claude bundle** (`plugins/claude/`): the Teammate-transport runtime mapping.
- **Packaged cross-adapter conformance** (`conformance/conformance.py`) + CI over the vendored bundles.

### Changed (vs. the Claude-only original)
- Durability is now a per-step write-ahead log with resume-from-partial (crash-safety the original lacked).
- The dead peer-to-peer "inbox" path is removed (it was never read mid-turn — stigmergy over a shared log).

### Notes
- Strategy A ("native blackboard") was chosen over an MCP coordinator after pre-flights on the real app;
  the MCP coordinator remains a dormant, gated fallback.
