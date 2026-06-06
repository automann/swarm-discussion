# swarm-discussion — plugin marketplace

A multi-expert **swarm discussion** for unsolved problems: it generates experts with a designed *tension
map*, runs blind position declarations → moderator framing → cited argumentation → a contrarian stress-test →
responses with position-shift tracking → cross-domain analogy → a quality gate, then synthesizes — with
per-step crash-safe checkpointing and a shift-provenance gate.

This repo is a **plugin marketplace** shipping the same skill for **both Claude Code and Codex**, built from
one shared core (no fork). Self-contained bundles live under `plugins/`.

## Install — Claude Code

```
/plugin marketplace add automann/swarm-discussion
/plugin install swarm-discussion@swarm-discussion
```
Then run, e.g.:
```
/swarm-discussion --mode lightweight "Should we use an append-only event log or mutable rows?"
```
Modes: `lightweight` (quick, cheap) · `standard` (default) · `deep`. Discussions are written under the current
workspace at `.swarm/discussions/<id>/`.

## Install — Codex

```
codex plugin marketplace add automann/swarm-discussion
```
The bundle ships the generic `swarm-expert` agent (`plugins/codex/agents/swarm-expert.toml`). Discussions are
written under the current workspace at `.swarm/discussions/<id>/`.

## How it works (one paragraph)

The orchestrator runs on the root thread and coordinates ephemeral persona subagents over a **shared on-disk
log** (a write-ahead log, not peer-to-peer messaging). The discussion *content* differs per host; the
*structure* (message-id chains, the argument graph, the round-record schema) is identical — guarded by the
bundled cross-adapter conformance test (`python3 conformance/conformance.py`).

## Footprint (please read before deep runs)

- Spawns **N persona subagents per step** (more in `standard`/`deep`) — real token cost; `lightweight` is the
  cheap tier for quick checks.
- **Writes files** under the project-scoped `discussionsRoot` (`.swarm/discussions` in the current workspace for
  both Claude Code and Codex; no network).
- Ships **no server** (Strategy A "native blackboard"). A dormant MCP coordinator exists in the design but is
  not shipped unless explicitly activated.

## Layout

```
.claude-plugin/marketplace.json   # Claude Code marketplace (lists the plugin below)
plugins/claude/                   # self-contained Claude Code plugin (skill + /swarm-discussion command)
plugins/codex/                    # self-contained Codex plugin (skill + swarm-expert agent)
```
Both bundles vendor the shared `protocol/` core; it is a vendored build artifact — don't edit it here.

## Maintainers — before you publish

1. Confirm `owner.url` / repository URLs (this README, `marketplace.json`, the two `plugin.json`s) match your
   actual GitHub path (defaults assume `automann/swarm-discussion`).
2. Re-run the packaged conformance/CI checks and validate the Codex manifest with Codex's `$plugin-creator`
   if the host schema has changed. Strategy A ships no MCP server, so no `mcpServers` entry is declared.
3. Verify on a clean host: install, run a `--mode lightweight` discussion, and validate a produced round with
   the bundled `protocol/validate_round.py`.
4. `git remote add origin …` and push. SemVer the plugins; keep `CHANGELOG.md` current.

## Credits

swarm-discussion is an independent, **self-contained** reimplementation that builds on and improves the
original **[swarm-discussion skill by Ischca](https://github.com/Ischca/swarm-discussion-skill)** (MIT).
Improvements over the original: a host-neutral shared core with thin Claude/Codex adapters (one skill, two
hosts), per-step write-ahead-log durability with crash-safe resume, context windowing with shift-provenance,
and a cross-adapter conformance test. This plugin does **not** depend on or require the original skill — it
ships everything it needs.

## License

MIT — see `LICENSE`.
