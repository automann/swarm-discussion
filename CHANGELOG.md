# Changelog

All notable changes to swarm-discussion. Versioning is SemVer; the on-disk data contract is versioned
separately as `schemaVersion` (see the vendored `protocol/SCHEMA.md` under each plugin bundle).

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
