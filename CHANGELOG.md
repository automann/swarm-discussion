# Changelog

All notable changes to swarm-discussion. Versioning is SemVer; the on-disk data contract is versioned
separately as `schemaVersion` (see the vendored `protocol/SCHEMA.md` under each plugin bundle).

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
- **Claude adapter** (`adapters/claude/`): the Teammate-transport reference mapping.
- **Packaged cross-adapter conformance** (`conformance/conformance.py`) + CI over the vendored bundles.

### Changed (vs. the Claude-only original)
- Durability is now a per-step write-ahead log with resume-from-partial (crash-safety the original lacked).
- The dead peer-to-peer "inbox" path is removed (it was never read mid-turn — stigmergy over a shared log).

### Notes
- Strategy A ("native blackboard") was chosen over an MCP coordinator after pre-flights on the real app
  recorded in the development repo; the MCP coordinator remains a dormant, gated fallback.
- The development repo also keeps the full review trail and source build script that produced these bundles.
