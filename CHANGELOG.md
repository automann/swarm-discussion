# Changelog

All notable changes to swarm-discussion. Versioning is SemVer; the on-disk data contract is versioned
separately as `schemaVersion` (see the vendored `protocol/SCHEMA.md` under each plugin bundle).

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
