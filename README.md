# 🐝 swarm-discussion

> **Stop your AI from agreeing with itself.** Convene a panel of expert personas who genuinely *argue* —
> with designed tension, blind position-taking, mandatory steel-manning, and a cited argument graph — then
> hand you a traceable synthesis.

This repository is the **aggregator marketplace** for the swarm-discussion plugin family. As of **v0.3** the
project is split:

- **[swarm-discussion-runtime](https://github.com/automann/swarm-discussion-runtime)** — the host-agnostic
  runtime and source of truth: discussion protocol semantics, prompt-build, fan-in, WAL, validation,
  trace/evidence, schemas, and the adapter certification gates.
- **host adapters**, one repo per coding agent, each a thin shell that vendors the runtime at a pinned SHA:
  - **[swarm-discussion-claude](https://github.com/automann/swarm-discussion-claude)** — the Claude Code
    adapter (orchestrator-as-sub-agent topology).
  - **[swarm-discussion-codex](https://github.com/automann/swarm-discussion-codex)** — the Codex adapter
    (parent-projected custom-agent experts plus a dedicated coordinator-thread topology).
- **this repo (`swarm-discussion`)** — a thin marketplace that points at **certified adapter releases**. It
  contains no protocol, runtime, or plugin code.

## Install (Claude Code)

```text
/plugin marketplace add automann/swarm-discussion
/plugin install swarm-discussion@swarm-discussion
```

Then invoke the skill (ask for a swarm discussion, or `/swarm-discussion`): the parent agent spawns a
`swarm-orchestrator` sub-agent that runs the whole discussion in its own context and returns only the
synthesis — discussion mechanics never enter your context window.

## Install (Codex)

```bash
codex plugin marketplace add automann/swarm-discussion
codex plugin add swarm-discussion --marketplace swarm-discussion
```

The Codex marketplace entry points at the root plugin repo
`automann/swarm-discussion-codex`, pinned to the certified adapter release
tag `v0.3.0`.

## Why it works

A single model role-playing experts drifts toward consensus. swarm-discussion engineers disagreement on
purpose: designed tension between opposing stakes, blind position declarations (no anchoring), mandatory
steel-manning before rebuttal, a cited argument graph (`supports`/`counters`/`extends`/`questions`),
position-shift tracking, a moderator quality gate, and a crash-safe write-ahead log. The full protocol lives
in the runtime's `protocol/` and is documented there.

## Versions

- **v0.3.x** — this aggregator + per-host adapters around the shared runtime, with dynamic custom-agent
  projection certification on both host adapters (current line).
- **v0.2.x** — the first thin-aggregator line around separately certified per-host adapters.
- **v0.1.x** — the previous single-repo, dual-host plugin (Claude + Codex bundled with a vendored runtime).
  Preserved at the **`v0.1.16` tag** and the **`v0.1.x` branch**; install instructions for that line live on the branch.

## For maintainers

This repo only lists certified adapter releases. To add or bump an adapter, edit the relevant host marketplace
manifest to point its `source` at the adapter repo and pin `ref` or `sha` to a certified release.

License: MIT (see `LICENSE`).
