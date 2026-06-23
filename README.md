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
    adapter (per-topic projected expert agents run by a coordinator background session).
  - **[swarm-discussion-codex](https://github.com/automann/swarm-discussion-codex)** — the Codex adapter
    (parent-projected custom-agent experts plus a dedicated coordinator-thread topology).
- **this repo (`swarm-discussion`)** — a thin marketplace that points at **certified adapter releases**. It
  contains no protocol, runtime, or plugin code.

## Install (Claude Code)

```text
/plugin marketplace add automann/swarm-discussion
/plugin install swarm-discussion@swarm-discussion
```

## Install (Codex)

```bash
codex plugin marketplace add automann/swarm-discussion
codex plugin add swarm-discussion --marketplace swarm-discussion
```

The Codex entry points at the root plugin repo `automann/swarm-discussion-codex`, pinned to the certified
release tag `v0.3.0`.

## Usage

Just ask in plain language, or run the skill directly:

```text
Use swarm-discussion to decide: should the orders service adopt event sourcing?
```

```text
/swarm-discussion
```

Bring the questions where a lone model would just nod along:

- ⚖️ **Architecture & design trade-offs** — *"modular monolith vs microservices for a team of six?"*
- 🚪 **One-way-door, high-stakes calls** — *"commit to Kafka, or stay on SQS another year?"*
- 🔎 **Adversarial review** — *"poke holes in this migration plan before we run it."*
- ❓ **Open questions where easy consensus would be suspicious.**

**What comes back** — not a wall of transcript — is a **recommendation**, the **strongest surviving
counter-argument**, the **open questions**, and pointers to the traceable artifacts (the cited argument
graph, synthesis, and trace/evidence). The debate runs in its own context, so your main session stays clean.

**Two knobs, set together.** `mode` controls *breadth & cost* (how many experts, how many rounds);
`stressPolicy` controls *how hard they must disagree* (whether a mandatory anti-consensus stress pass
runs before synthesis). They're orthogonal — combine them freely:

```text
/swarm-discussion [--mode lightweight|standard|deep] [--stressPolicy auto|required|off] <your question>
```

`stressPolicy` **defaults from `mode`** (`lightweight → off`, `standard → auto`, `deep → required`), so
usually you set neither — pick a mode by stakes, or just describe the problem (*"go **deep** and don't let
them agree too fast"* ≈ `--mode deep --stressPolicy required`). Pass `--stressPolicy` only to override that
default:

| Invocation | What runs |
|---|---|
| `/swarm-discussion Should we adopt event sourcing?` | inferred mode + its default stress policy |
| `/swarm-discussion --mode standard --stressPolicy auto <topic>` | 2–3 experts; stress pass *only if* they converge with no real disagreement |
| `/swarm-discussion --mode deep <topic>` | full panel + a `required` stress pass (deep's default) |
| `/swarm-discussion --mode lightweight --stressPolicy required <topic>` | cheap 2-expert panel, but still force one stress pass |

Both knobs are detailed below; it defaults to **standard** when you say nothing. The tiers:

## Modes

| Mode | Panel | Rounds | Calls/round | Use when |
|------|-------|--------|-------------|----------|
| `lightweight` | 2 dynamic experts + Moderator & Contrarian | 1–2 | 3–5 | quick sanity check, idea validation |
| `standard` *(default)* | 2–3 dynamic experts + 4 fixed roles | 2–3 | 5–8 | typical design decision, trade-off analysis |
| `deep` | 3–4 dynamic experts + 4 fixed roles | 3–5 | 8–12 | unprecedented problems, high-stakes calls |

> **Quality over quantity:** two rounds of *genuine* disagreement beat five rounds of polite agreement.

### Stress policy — engineering the disagreement

Orthogonal to `mode`, **`stressPolicy`** controls whether the panel must run an anti-consensus
**stress pass** (the Contrarian attacks the *strongest* agreement; the challenged experts answer
and may shift position) before it synthesizes:

| `stressPolicy` | Behavior | Default for |
|---|---|---|
| `required` | always run the stress pass, however smooth the round looks | `deep` |
| `auto` | run it only if the round reached consensus with no real disagreement | `standard` |
| `off` | no stress pass — fast convergence | `lightweight` |

You rarely set it (it defaults from the `mode`), but you can ask in plain language:
*"stress-test this"* / *"don't converge too fast"* → `required`. The runtime **certifies** that a
`required`/`auto` discussion actually engineered disagreement (a stress pass answered by a cited
response, or a recorded decision that none was needed) — a checked contract, not a suggestion.

Every panel runs **dynamic experts** generated per topic — each with explicit *stakes* and *blind spots* so
they argue with conviction — plus **fixed roles** that keep the debate honest:

| Role | Keeps the debate honest by… |
|------|------------------------------|
| 🧭 **Moderator** | framing the real fault lines and running the quality gate — *prevents premature consensus* |
| 🥊 **Contrarian** | stress-testing the *strongest* point of agreement — *prevents echo chambers* |
| 🔭 **Cross-Domain** *(standard / deep)* | bringing analogies from other fields — *prevents domain-locked thinking* |
| 📜 **Historian** *(standard / deep)* | building the cited argument graph and synthesis — *keeps it traceable* |

The full mode / role / round protocol lives in the runtime's
[`protocol/PROTOCOL.md`](https://github.com/automann/swarm-discussion-runtime/blob/main/protocol/PROTOCOL.md).

## Why it works

A single model role-playing experts drifts toward consensus. swarm-discussion engineers disagreement on
purpose: designed tension between opposing stakes, blind position declarations (no anchoring), mandatory
steel-manning before rebuttal, a cited argument graph (`supports`/`counters`/`extends`/`questions`),
position-shift tracking, a Moderator quality gate, and a crash-safe write-ahead log. The full protocol lives
in the runtime's `protocol/` and is documented there.

## Versions

- **v0.3.x** — this aggregator + per-host adapters around the shared runtime, with dynamic custom-agent
  projection certified on both host adapters (current line).
- **v0.2.x** — the first thin-aggregator line around separately certified per-host adapters.
- **v0.1.x** — the previous single-repo, dual-host plugin (Claude + Codex bundled with a vendored runtime).
  Preserved at the **`v0.1.16` tag** and the **`v0.1.x` branch**; install instructions for that line live on the branch.

## For maintainers

This repo only lists certified adapter releases. To add or bump an adapter, edit the relevant host marketplace
manifest to point its `source` at the adapter repo and pin `ref` or `sha` to a certified release.

License: MIT (see `LICENSE`).
