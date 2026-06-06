# 🐝 swarm-discussion

> **Stop your AI from agreeing with itself.** Convene a panel of expert personas who genuinely *argue* —
> with designed tension, blind position-taking, mandatory steel-manning, and a cited argument graph — then
> hand you a traceable synthesis.

For hard, open, or high-stakes questions, a single model tends to lock onto the first plausible answer.
**swarm-discussion** spins up several expert personas with *structurally opposing* stakes, makes each commit
a position **before** seeing the others (no anchoring), forces them to steel-man before they rebut, tracks
who changed whose mind and why, and closes with a synthesis where every claim cites a message ID.

One skill, two hosts: **Claude Code** and the **Codex desktop app**.

---

## Why it works

Experts role-played inside one model drift toward consensus: they agree with well-argued prior turns, add
instead of challenge, and converge too fast. swarm-discussion engineers disagreement on purpose:

- **🎯 Designed tension** — a *tension map* pairs experts whose roles/stakes genuinely conflict.
- **🙈 Blind position declarations** — each expert commits a stance (with `wouldChangeIf`) before seeing peers.
- **🥊 Mandatory steel-manning** — restate the opposing view at its strongest, *then* counter it.
- **🔗 Argument graph** — every message cites prior ones by ID (`supports` / `counters` / `extends` / `questions`).
- **🔀 Position-shift tracking** — records when an expert changes their mind and the exact message that moved them.
- **🚦 Quality gates** — the Moderator scores genuine disagreement and blocks premature consensus.
- **💾 Crash-safe & resumable** — a per-step write-ahead log; force-quit mid-discussion and pick up where it stopped.

## Good for

Architecture & design decisions · build-vs-buy · rewrite-vs-refactor · stress-testing a risky plan before you
commit · surfacing the blind spots no single perspective would catch.

---

## Install & use — Claude Code

```
/plugin marketplace add automann/swarm-discussion
/plugin install swarm-discussion@swarm-discussion
```

Then invoke the `/swarm-discussion` command with a topic:

```
/swarm-discussion "Should the orders service adopt event sourcing?"
/swarm-discussion --mode deep "Rewrite the monolith, or strangler-fig it?"
/swarm-discussion --mode lightweight "GraphQL or REST for this internal API?"
```

You'll be shown the proposed experts and their designed tensions to confirm before the debate begins; each
round then streams to the conversation. Results are saved under `.swarm/discussions/<id>/` in your workspace.

## Install & use — Codex desktop app

Install the Codex bundle straight from this repo (it lives at `plugins/codex`):

```
npx codex-marketplace add automann/swarm-discussion/plugins/codex --plugin
```

- Add `--project` to install into the current project only, or `--global` for every project — omit the flag
  and the CLI prompts you to choose.
- This registers the plugin in `~/.codex/config.toml`, caches it under `~/.codex/plugins/cache/`, and installs
  the bundled `swarm-discussion` skill and the generic `swarm-expert` agent.

Then, in the Codex app, start it on a **top-level thread** — type `@` and pick **swarm-discussion**, or just
ask in plain language:

```
@ swarm-discussion — run a lightweight discussion on: append-only event log vs mutable rows
```
> *"Use swarm-discussion to stress-test this decision: should we shard the database now or after launch? Go deep."*

Codex spawns the expert personas as subagents and writes the discussion under `.swarm/discussions/<id>/` in
your workspace.

**Codex notes**
- Run it on the **root thread** — the orchestrator coordinates subagents and can't itself be a subagent
  (`agents.max_depth = 1`).
- Codex needs write access to your workspace; it only ever writes under `.swarm/discussions/`.
- To turn the plugin off without uninstalling, set its entry in `~/.codex/config.toml` to `enabled = false`
  and restart Codex.

---

## Modes

Pick a tier by stakes and budget (`--mode` on Claude Code, or say it in your request on Codex):

| Mode | Experts | Rounds | Calls/round | Use when |
|------|---------|--------|-------------|----------|
| `lightweight` | 2 dynamic + Moderator & Contrarian | 1–2 | 3–5 | quick sanity check, idea validation |
| `standard` *(default)* | 2–3 dynamic + 4 fixed | 2–3 | 5–8 | typical design decision, tradeoff analysis |
| `deep` | 3–4 dynamic + 4 fixed | 3–5 | 8–12 | unprecedented problems, high-stakes calls |

> Quality over quantity: two rounds of *genuine* disagreement beat five rounds of polite agreement.

**Roles.** Every panel has a **Moderator** (frames real fault lines, runs the quality gate) and a
**Contrarian** (attacks the *strongest* consensus). Standard/Deep add a **Cross-Domain** thinker (analogies
from other fields) and a **Historian** (argument graph + synthesis). The **dynamic experts** are generated
per topic, each with explicit *stakes* and *blind spots* so they argue with conviction.

## What a run produces

Everything is saved, inspectable, and resumable, under `.swarm/discussions/<id>/`:

```
manifest.json            # topic, mode, personas, tension map, status
progress.md              # live per-step log you can tail
personas/<id>.json       # each expert: expertise, bias, stakes, blind spots
rounds/NNN.json          # messages + argument graph + position shifts + quality score
artifacts/               # synthesis, open questions, argument graph, position evolution
```

You can validate any committed round with the bundled `protocol/validate_round.py`:

```
python3 .../skills/swarm-discussion/protocol/validate_round.py .swarm/discussions/<id>/rounds/001.json
```

## How it works (under the hood)

The orchestrator runs on your main thread and coordinates ephemeral persona subagents over a **shared on-disk
write-ahead log** — a *blackboard*, not peer-to-peer messaging. It mints durable message IDs (so a resume
never restarts numbering), windows each persona's view of the log (you always see your own history in full;
peers are summarized past a budget), and runs a **provenance gate** — a recorded "I changed my mind because
of `r1-msg-006`" must cite a message that persona was actually shown. The discussion *content* differs by
host; the *structure* (ID chains, argument graph, round schema) is identical across both — verified by the
bundled cross-adapter conformance test (`python3 conformance/conformance.py`).

It ships **no server** ("native blackboard").

## Footprint & cost

- Spawns **N persona subagents per step** (more in `standard`/`deep`) — real token/API cost. `lightweight` is
  the cheap tier; reach for `deep` only when the decision earns it.
- **Writes files** under `.swarm/discussions/` in the current workspace. No network calls.

## Layout

```
.claude-plugin/marketplace.json   # Claude Code marketplace entry
plugins/claude/                   # Claude Code plugin (skill + /swarm-discussion command)
plugins/codex/                    # Codex plugin (skill + swarm-expert agent)
conformance/                      # cross-bundle conformance test
```

Both bundles vendor the shared `protocol/` core; it is a vendored build artifact — don't edit it here.

## Credits

swarm-discussion is an independent, **self-contained** reimplementation that builds on and improves the
original **[swarm-discussion skill by Ischca](https://github.com/Ischca/swarm-discussion-skill)** (MIT).
Improvements over the original: a shared core with thin Claude/Codex adapters (one skill, two hosts), per-step
write-ahead-log durability with crash-safe resume, context windowing with shift-provenance, and a
cross-adapter conformance test. This plugin does **not** depend on or require the original skill — it ships
everything it needs.

## License

MIT — see [`LICENSE`](LICENSE).
